from __future__ import annotations

import atexit
import json
import os
import queue
import re
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from ..sanitizer.sanitizer import (
    SanitizationResult,
    SanitizerConfig,
    sanitize_artifact_dict,
    sanitize_source,
)

ExecutionMode = Literal["oneshot_cli", "persistent_server", "auto"]
_LIVE_RUNNERS: set["LeanCheckerRunner"] = set()


def _close_all_live_runners() -> None:
    for runner in list(_LIVE_RUNNERS):
        try:
            runner.close()
        except Exception:
            pass


atexit.register(_close_all_live_runners)


@dataclass(slots=True)
class CheckerRunConfig:
    lean_executable: str = "lean"
    timeout_seconds: int = 20
    workdir: str | None = None
    min_lean_version: tuple[int, int, int] = (4, 22, 0)
    required_lean_version: tuple[int, int, int] | None = None
    execution_mode: ExecutionMode = "oneshot_cli"
    persistent_restart_budget: int = 1
    persistent_settle_seconds: float = 0.25
    persistent_startup_timeout_seconds: int = 8
    persistent_fallback_to_oneshot: bool = True
    persistent_workers: int = 1
    persistent_queue_timeout_seconds: float = 30.0
    preflight_timeout_seconds: int = 30


@dataclass(slots=True)
class CheckerRunResult:
    success: bool
    returncode: int | None
    stdout: str
    stderr: str
    duration_ms: int
    timed_out: bool
    sanitizer_result: SanitizationResult | None = None
    backend_mode: str = "oneshot_cli"
    fallback_used: bool = False
    backend_error: bool = False


LeanCheckResult = CheckerRunResult


class _PersistentLeanServerBackend:
    """Lean LSP server-backed persistent checker backend."""

    def __init__(self, config: CheckerRunConfig):
        self._config = config
        self._proc: subprocess.Popen[bytes] | None = None
        self._stdout_thread: threading.Thread | None = None
        self._messages: queue.Queue[dict[str, Any] | None] = queue.Queue()
        self._request_id = 1
        self._doc_version = 1
        self._doc_uri: str | None = None
        self._doc_open = False
        self._running = False
        self._lock = threading.Lock()

    def close(self) -> None:
        with self._lock:
            self._shutdown_locked()

    def is_alive(self) -> bool:
        proc = self._proc
        return self._running and proc is not None and proc.poll() is None

    def run_source(
        self,
        source: str,
        sanitizer_result: SanitizationResult | None,
    ) -> CheckerRunResult:
        with self._lock:
            started, err = self._ensure_started_locked()
            if not started:
                return _backend_error_result(
                    err or "Failed to initialize persistent Lean worker.",
                    sanitizer_result,
                    backend_mode="persistent_server",
                )

            start = time.perf_counter()
            uri = self._doc_uri
            if not uri:
                root_path = Path(self._config.workdir or os.getcwd()).resolve()
                uri = (root_path / f".lkv_worker_{id(self)}.lean").as_uri()
                self._doc_uri = uri
            version = self._doc_version
            self._doc_version += 1

            try:
                if not self._doc_open:
                    self._send_notification_locked(
                        {
                            "jsonrpc": "2.0",
                            "method": "textDocument/didOpen",
                            "params": {
                                "textDocument": {
                                    "uri": uri,
                                    "languageId": "lean4",
                                    "version": version,
                                    "text": source,
                                }
                            },
                        }
                    )
                    self._doc_open = True
                else:
                    self._send_notification_locked(
                        {
                            "jsonrpc": "2.0",
                            "method": "textDocument/didChange",
                            "params": {
                                "textDocument": {
                                    "uri": uri,
                                    "version": version,
                                },
                                "contentChanges": [{"text": source}],
                            },
                        }
                    )
            except OSError as exc:
                self._shutdown_locked()
                duration_ms = int((time.perf_counter() - start) * 1000)
                return _backend_error_result(
                    f"Persistent worker write failure: {exc}.",
                    sanitizer_result,
                    duration_ms=duration_ms,
                    backend_mode="persistent_server",
                )

            return self._collect_diagnostics_locked(
                uri=uri,
                version=version,
                start_time=start,
                sanitizer_result=sanitizer_result,
            )

    def _collect_diagnostics_locked(
        self,
        *,
        uri: str,
        version: int,
        start_time: float,
        sanitizer_result: SanitizationResult | None,
    ) -> CheckerRunResult:
        latest_diagnostics: list[dict[str, Any]] | None = None
        processing_active = False
        saw_relevant_event = False
        last_relevant_event = time.perf_counter()
        deadline = start_time + max(1, self._config.timeout_seconds)

        while True:
            now = time.perf_counter()
            remaining = deadline - now
            if remaining <= 0:
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                return CheckerRunResult(
                    success=False,
                    returncode=None,
                    stdout="",
                    stderr="Persistent Lean worker timed out waiting for diagnostics.",
                    duration_ms=duration_ms,
                    timed_out=True,
                    sanitizer_result=sanitizer_result,
                    backend_mode="persistent_server",
                    fallback_used=False,
                    backend_error=False,
                )

            message = self._poll_message_locked(timeout=min(0.1, remaining))
            if message is None:
                if (
                    saw_relevant_event
                    and latest_diagnostics is not None
                    and not processing_active
                    and (time.perf_counter() - last_relevant_event) >= self._config.persistent_settle_seconds
                ):
                    break
                continue

            method = message.get("method")
            if method == "$/lean/fileProgress":
                params = message.get("params", {})
                text_doc = params.get("textDocument", {})
                if text_doc.get("uri") == uri and int(text_doc.get("version", version)) == version:
                    processing = params.get("processing", [])
                    processing_active = bool(processing)
                    saw_relevant_event = True
                    last_relevant_event = time.perf_counter()
                continue

            if method == "textDocument/publishDiagnostics":
                params = message.get("params", {})
                if params.get("uri") == uri and int(params.get("version", version)) == version:
                    diagnostics = params.get("diagnostics", [])
                    if isinstance(diagnostics, list):
                        latest_diagnostics = diagnostics
                    else:
                        latest_diagnostics = []
                    saw_relevant_event = True
                    last_relevant_event = time.perf_counter()
                continue

        diagnostics = latest_diagnostics or []
        errors = [d for d in diagnostics if int(d.get("severity", 1)) <= 1]
        warnings = [d for d in diagnostics if int(d.get("severity", 2)) > 1]
        duration_ms = int((time.perf_counter() - start_time) * 1000)

        return CheckerRunResult(
            success=not errors,
            returncode=0 if not errors else 1,
            stdout="\n".join(_format_diag(item) for item in warnings),
            stderr="\n".join(_format_diag(item) for item in errors),
            duration_ms=duration_ms,
            timed_out=False,
            sanitizer_result=sanitizer_result,
            backend_mode="persistent_server",
            fallback_used=False,
            backend_error=False,
        )

    def _ensure_started_locked(self) -> tuple[bool, str | None]:
        if self._running and self._proc is not None and self._proc.poll() is None:
            return True, None

        self._shutdown_locked()
        cmd = [self._config.lean_executable, "--server"]
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self._config.workdir or os.getcwd(),
            )
        except FileNotFoundError:
            return False, f"Lean executable `{self._config.lean_executable}` not found."
        except OSError as exc:
            return False, f"Persistent worker start failed: {exc}."

        if self._proc.stdin is None or self._proc.stdout is None:
            self._shutdown_locked()
            return False, "Persistent worker failed: missing stdio pipes."

        self._messages = queue.Queue()
        self._stdout_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._stdout_thread.start()

        root_path = Path(self._config.workdir or os.getcwd()).resolve()
        self._doc_uri = (root_path / f".lkv_worker_{id(self)}.lean").as_uri()
        self._doc_open = False
        initialize_request = {
            "jsonrpc": "2.0",
            "id": self._next_request_id_locked(),
            "method": "initialize",
            "params": {
                "processId": None,
                "rootUri": root_path.as_uri(),
                "capabilities": {},
            },
        }
        try:
            self._send_frame_locked(initialize_request)
        except OSError as exc:
            self._shutdown_locked()
            return False, f"Persistent worker initialize send failed: {exc}."

        response = self._wait_for_response_locked(
            request_id=int(initialize_request["id"]),
            timeout_seconds=max(1, self._config.persistent_startup_timeout_seconds),
        )
        if response is None:
            self._shutdown_locked()
            return False, "Persistent worker initialize timed out."
        if "error" in response:
            self._shutdown_locked()
            return False, f"Persistent worker initialize failed: {response['error']}."

        try:
            self._send_notification_locked(
                {"jsonrpc": "2.0", "method": "initialized", "params": {}}
            )
        except OSError as exc:
            self._shutdown_locked()
            return False, f"Persistent worker post-initialize send failed: {exc}."

        self._running = True
        return True, None

    def _wait_for_response_locked(
        self,
        *,
        request_id: int,
        timeout_seconds: float,
    ) -> dict[str, Any] | None:
        deadline = time.perf_counter() + max(0.1, timeout_seconds)
        while True:
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                return None
            message = self._poll_message_locked(timeout=min(0.1, remaining))
            if message is None:
                continue
            msg_id = message.get("id")
            if (isinstance(msg_id, int) and msg_id == request_id) or (
                isinstance(msg_id, str) and msg_id == str(request_id)
            ):
                return message

    def _poll_message_locked(self, timeout: float) -> dict[str, Any] | None:
        try:
            message = self._messages.get(timeout=timeout)
        except queue.Empty:
            return None

        if message is None:
            self._shutdown_locked()
            raise OSError("Persistent Lean worker stream closed.")

        if message.get("method") == "client/registerCapability" and "id" in message:
            try:
                self._send_frame_locked(
                    {"jsonrpc": "2.0", "id": message["id"], "result": None}
                )
            except OSError:
                self._shutdown_locked()
                raise
            return None
        return message

    def _next_request_id_locked(self) -> int:
        self._request_id += 1
        return self._request_id

    def _send_notification_locked(self, payload: dict[str, Any]) -> None:
        self._send_frame_locked(payload)

    def _send_frame_locked(self, payload: dict[str, Any]) -> None:
        if self._proc is None or self._proc.stdin is None:
            raise OSError("Persistent Lean worker is not running.")
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        frame = f"Content-Length: {len(data)}\r\n\r\n".encode("ascii") + data
        self._proc.stdin.write(frame)
        self._proc.stdin.flush()

    def _reader_loop(self) -> None:
        try:
            if self._proc is None or self._proc.stdout is None:
                self._messages.put(None)
                return

            stream = self._proc.stdout
            while True:
                headers: dict[str, str] = {}
                while True:
                    line = stream.readline()
                    if line == b"":
                        self._messages.put(None)
                        return
                    if line in (b"\r\n", b"\n"):
                        break
                    try:
                        decoded = line.decode("utf-8", "replace").strip()
                    except Exception:
                        decoded = ""
                    if ":" in decoded:
                        key, value = decoded.split(":", 1)
                        headers[key.strip().lower()] = value.strip()

                content_length_text = headers.get("content-length")
                if content_length_text is None:
                    continue
                try:
                    content_length = int(content_length_text)
                except ValueError:
                    continue
                if content_length < 0:
                    continue

                body = stream.read(content_length)
                if len(body) != content_length:
                    self._messages.put(None)
                    return
                try:
                    message = json.loads(body.decode("utf-8", "replace"))
                except json.JSONDecodeError:
                    continue
                if isinstance(message, dict):
                    self._messages.put(message)
        except Exception:
            self._messages.put(None)

    def _shutdown_locked(self) -> None:
        proc = self._proc
        reader = self._stdout_thread
        self._stdout_thread = None
        if proc is None:
            if reader is not None and reader.is_alive() and reader is not threading.current_thread():
                reader.join(timeout=0.5)
            return
        try:
            if proc.poll() is None:
                try:
                    self._send_frame_to_proc(
                        proc,
                        {"jsonrpc": "2.0", "id": self._next_request_id_locked(), "method": "shutdown", "params": None},
                    )
                except Exception:
                    pass
                try:
                    self._send_frame_to_proc(proc, {"jsonrpc": "2.0", "method": "exit", "params": None})
                except Exception:
                    pass
                proc.terminate()
                proc.wait(timeout=1)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        finally:
            for stream_name in ("stdin", "stdout", "stderr"):
                stream = getattr(proc, stream_name, None)
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass
            self._proc = None
            self._running = False
            self._doc_open = False
            self._doc_uri = None
            if reader is not None and reader.is_alive() and reader is not threading.current_thread():
                reader.join(timeout=0.5)

    @staticmethod
    def _send_frame_to_proc(proc: subprocess.Popen[bytes], payload: dict[str, Any]) -> None:
        if proc.stdin is None:
            raise OSError("Persistent Lean worker stdin is unavailable.")
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        frame = f"Content-Length: {len(data)}\r\n\r\n".encode("ascii") + data
        proc.stdin.write(frame)
        proc.stdin.flush()


class LeanCheckerRunner:
    def __init__(self, config: CheckerRunConfig | None = None):
        self.config = config or CheckerRunConfig()
        self._preflight_checked = False
        self._preflight_error: str | None = None
        self._preflight_timed_out = False
        self._persistent_backend: _PersistentLeanServerBackend | None = None
        self._persistent_pool: list[_PersistentLeanServerBackend | None] | None = None
        self._persistent_pool_locks: list[threading.Lock] = []
        self._persistent_pool_rr_index = 0
        self._persistent_pool_dispatch_lock = threading.Lock()
        self._persistent_pool_semaphore: threading.BoundedSemaphore | None = None
        self._persistent_startups = 0
        self._persistent_restarts = 0
        self._persistent_backend_errors = 0
        self._persistent_requests = 0
        self._fallback_to_oneshot_count = 0
        _LIVE_RUNNERS.add(self)

    def close(self) -> None:
        if self._persistent_pool is not None:
            for backend in self._persistent_pool:
                if backend is not None:
                    backend.close()
            self._persistent_pool = None
        self._persistent_pool_locks = []
        self._persistent_pool_semaphore = None
        self._persistent_backend = None
        _LIVE_RUNNERS.discard(self)

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass

    def telemetry_snapshot(self) -> dict[str, int | str]:
        active_slots = self._active_persistent_slots()
        return {
            "configured_execution_mode": self.config.execution_mode,
            "persistent_workers_configured": max(1, int(self.config.persistent_workers)),
            "persistent_worker_slots_active": active_slots,
            "persistent_startups": self._persistent_startups,
            "persistent_restarts": self._persistent_restarts,
            "persistent_requests": self._persistent_requests,
            "persistent_backend_errors": self._persistent_backend_errors,
            "fallback_to_oneshot_count": self._fallback_to_oneshot_count,
        }

    def run_source(
        self,
        source: str,
        sanitizer_config: SanitizerConfig | None = None,
        sanitize_first: bool = True,
    ) -> CheckerRunResult:
        if not sanitize_first:
            return CheckerRunResult(
                success=False,
                returncode=None,
                stdout="",
                stderr=(
                    "Sanitization bypass is disallowed by contract: "
                    "S1.5 sanitizer pass is mandatory."
                ),
                duration_ms=0,
                timed_out=False,
                sanitizer_result=None,
            )

        sanitizer_result = sanitize_source(source, sanitizer_config)
        if not sanitizer_result.passed:
            return CheckerRunResult(
                success=False,
                returncode=None,
                stdout="",
                stderr="\n".join(sanitizer_result.errors),
                duration_ms=0,
                timed_out=False,
                sanitizer_result=sanitizer_result,
            )

        preflight_error = self._ensure_lean_compatible()
        if preflight_error is not None:
            return CheckerRunResult(
                success=False,
                returncode=None,
                stdout="",
                stderr=preflight_error,
                duration_ms=0,
                timed_out=self._preflight_timed_out,
                sanitizer_result=sanitizer_result,
                backend_error=True,
            )

        return self._run_checked_source(
            source=sanitizer_result.sanitized_source,
            sanitizer_result=sanitizer_result,
        )

    def verify_artifact_dict(
        self,
        artifact_data: dict[str, Any],
        sanitizer_config: SanitizerConfig | None = None,
    ) -> CheckerRunResult:
        sanitizer_result = sanitize_artifact_dict(artifact_data, sanitizer_config)
        if not sanitizer_result.passed:
            return CheckerRunResult(
                success=False,
                returncode=None,
                stdout="",
                stderr="\n".join(sanitizer_result.errors),
                duration_ms=0,
                timed_out=False,
                sanitizer_result=sanitizer_result,
            )

        preflight_error = self._ensure_lean_compatible()
        if preflight_error is not None:
            return CheckerRunResult(
                success=False,
                returncode=None,
                stdout="",
                stderr=preflight_error,
                duration_ms=0,
                timed_out=self._preflight_timed_out,
                sanitizer_result=sanitizer_result,
                backend_error=True,
            )
        return self._run_checked_source(
            source=sanitizer_result.sanitized_source,
            sanitizer_result=sanitizer_result,
        )

    def _run_checked_source(
        self,
        *,
        source: str,
        sanitizer_result: SanitizationResult | None,
    ) -> CheckerRunResult:
        mode = self.config.execution_mode
        if mode == "oneshot_cli":
            return self._run_lean_file(source, sanitizer_result, backend_mode="oneshot_cli")

        result = self._run_persistent_backend(source, sanitizer_result)
        # An empty LSP diagnostic batch can precede completion of elaboration.
        # A quiet interval is not evidence that the theorem has been checked.
        if result.success:
            return self._run_lean_file(
                source, sanitizer_result, backend_mode="persistent_confirmed_cli",
            )
        persistent_timeout = result.backend_mode == "persistent_server" and result.timed_out
        if not result.backend_error and not persistent_timeout:
            return result

        if mode == "persistent_server" and not self.config.persistent_fallback_to_oneshot:
            return result
        if mode == "auto" and not self.config.persistent_fallback_to_oneshot:
            return result

        self._fallback_to_oneshot_count += 1
        fallback = self._run_lean_file(
            source,
            sanitizer_result,
            backend_mode="oneshot_cli_fallback",
        )
        fallback.fallback_used = True
        return fallback

    def _run_persistent_backend(
        self,
        source: str,
        sanitizer_result: SanitizationResult | None,
    ) -> CheckerRunResult:
        self._ensure_persistent_pool()
        if self._persistent_pool is None or self._persistent_pool_semaphore is None:
            return _backend_error_result(
                "Persistent worker pool failed to initialize.",
                sanitizer_result,
                backend_mode="persistent_server",
            )
        acquired = self._persistent_pool_semaphore.acquire(
            timeout=max(0.0, float(self.config.persistent_queue_timeout_seconds))
        )
        if not acquired:
            return _backend_error_result(
                (
                    "Persistent worker pool queue timed out waiting for an available slot "
                    f"(workers={max(1, int(self.config.persistent_workers))})."
                ),
                sanitizer_result,
                backend_mode="persistent_server",
            )
        try:
            slot_index = self._next_persistent_slot()
            return self._run_persistent_backend_slot(
                slot_index=slot_index,
                source=source,
                sanitizer_result=sanitizer_result,
            )
        finally:
            self._persistent_pool_semaphore.release()

    def _run_persistent_backend_slot(
        self,
        *,
        slot_index: int,
        source: str,
        sanitizer_result: SanitizationResult | None,
    ) -> CheckerRunResult:
        if self._persistent_pool is None:
            return _backend_error_result(
                "Persistent worker pool not initialized.",
                sanitizer_result,
                backend_mode="persistent_server",
            )
        if not (0 <= slot_index < len(self._persistent_pool)):
            return _backend_error_result(
                f"Persistent worker slot index out of range: {slot_index}.",
                sanitizer_result,
                backend_mode="persistent_server",
            )
        slot_lock = self._persistent_pool_locks[slot_index]
        attempts = max(1, self.config.persistent_restart_budget + 1)
        last_result: CheckerRunResult | None = None

        with slot_lock:
            for attempt in range(attempts):
                backend = self._persistent_pool[slot_index]
                if backend is not None and not backend.is_alive():
                    self._persistent_restarts += 1
                    backend.close()
                    self._persistent_pool[slot_index] = None
                    backend = None

                if backend is None:
                    backend = _PersistentLeanServerBackend(self.config)
                    self._persistent_pool[slot_index] = backend
                    self._persistent_startups += 1
                    if slot_index == 0:
                        self._persistent_backend = backend

                self._persistent_requests += 1
                try:
                    result = backend.run_source(source, sanitizer_result)
                except OSError as exc:
                    result = _backend_error_result(
                        f"Persistent worker transport failure: {exc}.",
                        sanitizer_result,
                        backend_mode="persistent_server",
                    )
                last_result = result
                if not result.backend_error:
                    return result

                self._persistent_backend_errors += 1
                if attempt + 1 < attempts:
                    self._persistent_restarts += 1
                    current = self._persistent_pool[slot_index]
                    if current is not None:
                        current.close()
                    self._persistent_pool[slot_index] = None
                    if slot_index == 0:
                        self._persistent_backend = None

        if last_result is None:
            return _backend_error_result(
                "Persistent worker failed without result.",
                sanitizer_result,
                backend_mode="persistent_server",
            )
        return last_result

    def _ensure_persistent_pool(self) -> None:
        if self._persistent_pool is not None:
            return
        workers = max(1, int(self.config.persistent_workers))
        self._persistent_pool = [None] * workers
        self._persistent_pool_locks = [threading.Lock() for _ in range(workers)]
        self._persistent_pool_rr_index = 0
        self._persistent_pool_semaphore = threading.BoundedSemaphore(workers)

    def _next_persistent_slot(self) -> int:
        if self._persistent_pool is None or not self._persistent_pool:
            return 0
        with self._persistent_pool_dispatch_lock:
            index = self._persistent_pool_rr_index % len(self._persistent_pool)
            self._persistent_pool_rr_index = (self._persistent_pool_rr_index + 1) % len(
                self._persistent_pool
            )
            return index

    def _active_persistent_slots(self) -> int:
        if self._persistent_pool is None:
            return 0
        return sum(1 for backend in self._persistent_pool if backend is not None and backend.is_alive())

    def _ensure_lean_compatible(self) -> str | None:
        if self._preflight_checked:
            return self._preflight_error

        self._preflight_checked = True
        self._preflight_error = None
        self._preflight_timed_out = False
        required = self.config.min_lean_version
        required_text = f"{required[0]}.{required[1]}.{required[2]}"

        try:
            proc = subprocess.run(
                [self.config.lean_executable, "--version"],
                capture_output=True,
                text=True,
                timeout=self.config.preflight_timeout_seconds,
            )
        except FileNotFoundError:
            self._preflight_error = f"Lean executable `{self.config.lean_executable}` not found."
            return self._preflight_error
        except subprocess.TimeoutExpired:
            # Load-related startup failures must not poison this runner forever.
            self._preflight_checked = False
            self._preflight_timed_out = True
            self._preflight_error = (
                f"Lean preflight timed out while checking `{self.config.lean_executable} --version`."
            )
            return self._preflight_error
        except OSError as exc:
            self._preflight_error = (
                f"Lean executable `{self.config.lean_executable}` could not be executed: {exc}."
            )
            return self._preflight_error

        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout).strip()
            self._preflight_error = (
                f"Lean preflight failed for `{self.config.lean_executable} --version` "
                f"(exit {proc.returncode}). {detail}"
            ).strip()
            return self._preflight_error

        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        match = re.search(r"version\s+(\d+)\.(\d+)\.(\d+)", output)
        if match is None:
            self._preflight_error = (
                f"Lean preflight failed: unable to parse version from `{self.config.lean_executable} --version`."
            )
            return self._preflight_error

        detected = tuple(int(match.group(i)) for i in (1, 2, 3))
        exact = self.config.required_lean_version
        if exact is not None and detected != exact:
            detected_text = f"{detected[0]}.{detected[1]}.{detected[2]}"
            exact_text = f"{exact[0]}.{exact[1]}.{exact[2]}"
            self._preflight_error = (
                f"Lean {detected_text} does not match required version {exact_text}."
            )
            return self._preflight_error
        if detected < required:
            detected_text = f"{detected[0]}.{detected[1]}.{detected[2]}"
            self._preflight_error = (
                f"Lean {detected_text} is below required >= {required_text}."
            )
            return self._preflight_error

        return None

    def _run_lean_file(
        self,
        source: str,
        sanitizer_result: SanitizationResult | None,
        *,
        backend_mode: str,
    ) -> CheckerRunResult:
        start = time.perf_counter()
        tmp_dir: tempfile.TemporaryDirectory[str] | None = None

        try:
            tmp_dir = tempfile.TemporaryDirectory(prefix="lkv_", dir=self.config.workdir)
            lean_file = Path(tmp_dir.name) / "verify.lean"
            lean_file.write_text(source, encoding="utf-8")
        except OSError as exc:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return CheckerRunResult(
                success=False,
                returncode=None,
                stdout="",
                stderr=f"Lean checker workspace or execution setup failed: {exc}.",
                duration_ms=duration_ms,
                timed_out=False,
                sanitizer_result=sanitizer_result,
                backend_mode=backend_mode,
                fallback_used=False,
                backend_error=True,
            )

        try:
            proc = subprocess.run(
                [self.config.lean_executable, str(lean_file)],
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
            )
            duration_ms = int((time.perf_counter() - start) * 1000)
            success = proc.returncode == 0
            return CheckerRunResult(
                success=success,
                returncode=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                duration_ms=duration_ms,
                timed_out=False,
                sanitizer_result=sanitizer_result,
                backend_mode=backend_mode,
                fallback_used=False,
                backend_error=False,
            )
        except subprocess.TimeoutExpired as exc:
            duration_ms = int((time.perf_counter() - start) * 1000)
            stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
            stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
            return CheckerRunResult(
                success=False,
                returncode=None,
                stdout=stdout,
                stderr=stderr or "Lean checker timed out.",
                duration_ms=duration_ms,
                timed_out=True,
                sanitizer_result=sanitizer_result,
                backend_mode=backend_mode,
                fallback_used=False,
                backend_error=False,
            )
        except FileNotFoundError:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return CheckerRunResult(
                success=False,
                returncode=None,
                stdout="",
                stderr=f"Lean executable `{self.config.lean_executable}` not found.",
                duration_ms=duration_ms,
                timed_out=False,
                sanitizer_result=sanitizer_result,
                backend_mode=backend_mode,
                fallback_used=False,
                backend_error=True,
            )
        finally:
            if tmp_dir is not None:
                tmp_dir.cleanup()


def _format_diag(diag: dict[str, Any]) -> str:
    message = str(diag.get("message", "")).strip()
    range_obj = diag.get("range", {})
    start = range_obj.get("start", {})
    line = int(start.get("line", 0)) + 1
    character = int(start.get("character", 0)) + 1
    return f"[{line}:{character}] {message}".strip()


def _backend_error_result(
    message: str,
    sanitizer_result: SanitizationResult | None,
    *,
    duration_ms: int = 0,
    backend_mode: str = "persistent_server",
) -> CheckerRunResult:
    return CheckerRunResult(
        success=False,
        returncode=None,
        stdout="",
        stderr=message,
        duration_ms=duration_ms,
        timed_out=False,
        sanitizer_result=sanitizer_result,
        backend_mode=backend_mode,
        fallback_used=False,
        backend_error=True,
    )
