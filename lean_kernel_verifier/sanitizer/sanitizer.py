from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..core.contracts import LeanCheckerArtifact, validate_artifact_schema

BANNED_ATTRIBUTES = {"implemented_by", "extern", "csimp"}
BANNED_DECLARATION_KEYWORDS = {
    "unsafe", "partial", "opaque", "axiom", "attribute", "initialize",
    "builtin_initialize", "run_cmd", "elab", "macro", "syntax",
}
DISALLOWED_PROOF_PLACEHOLDERS = {"sorry", "admit"}
ALLOWED_SET_OPTIONS = {"maxRecDepth", "maxHeartbeats"}
REQUIRED_TEMPLATE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("set_option maxRecDepth", re.compile(r"^\s*set_option\s+maxRecDepth\b", re.MULTILINE)),
    ("set_option maxHeartbeats", re.compile(r"^\s*set_option\s+maxHeartbeats\b", re.MULTILINE)),
    ("def powMod", re.compile(r"^\s*def\s+powMod\b", re.MULTILINE)),
    ("def factorial", re.compile(r"^\s*def\s+factorial\b", re.MULTILINE)),
    ("def choose", re.compile(r"^\s*def\s+choose\b", re.MULTILINE)),
    ("formula definition `def f`", re.compile(r"^\s*def\s+f\b", re.MULTILINE)),
    ("def expected", re.compile(r"^\s*def\s+expected\b", re.MULTILINE)),
    ("theorem verify", re.compile(r"^\s*theorem\s+verify\b", re.MULTILINE)),
)

ATTRIBUTE_BLOCK_RE = re.compile(r"@\[\s*([^\]]+?)\s*\]", re.DOTALL)
IMPORT_RE = re.compile(r"^\s*import\s+(.+?)\s*$")
SET_OPTION_RE = re.compile(r"^\s*set_option\s+([A-Za-z0-9_.]+)")
DECL_KEYWORD_RE = re.compile(r"\b(" + "|".join(sorted(BANNED_DECLARATION_KEYWORDS)) + r")\b")
PLACEHOLDER_KEYWORD_RE = re.compile(r"\b(sorry|admit)\b")
VERIFY_THEOREM_RE = re.compile(r"^\s*theorem\s+verify\b")
TOP_LEVEL_DECL_RE = re.compile(
    r"^(import|open|namespace|section|end|set_option|def|abbrev|theorem|lemma|example|"
    r"axiom|inductive|structure|class|instance|#)"
)
TACTIC_TOKEN_RE = re.compile(r"\b(native_decide|grind)\b")
STRING_LITERAL_RE = re.compile(r'"(?:\\.|[^"\\])*"')
VERIFY_HEADER_RE = re.compile(
    r"^\s*theorem\s+verify\s*:\s*(?P<statement>.*?)\s*:=\s*by\s*$",
    re.DOTALL,
)
NATIVE_VERIFY_SHAPE_EXACT = (
    "(Array.range expected.size).all (fun n => f n == expected[n]!) = true"
)


@dataclass(slots=True)
class SanitizerConfig:
    profile: str = "A"
    strict_schema: bool = True
    enforce_template_contract: bool = True


@dataclass(slots=True)
class SanitizationResult:
    sanitized_source: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stripped_attributes: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors


def sanitize_source(source: str, config: SanitizerConfig | None = None) -> SanitizationResult:
    cfg = config or SanitizerConfig()
    errors: list[str] = []
    warnings: list[str] = []
    stripped_attributes: list[str] = []
    sanitized_lines: list[str] = []
    source = _strip_banned_attributes(source, stripped_attributes)
    code_only_source = _strip_comments_preserving_lines(source)
    code_only_lines = code_only_source.splitlines()

    for line_no, raw_line in enumerate(source.splitlines(), start=1):
        sanitized_line = raw_line
        code_portion = ""
        if line_no - 1 < len(code_only_lines):
            code_portion = code_only_lines[line_no - 1].strip()
        code_without_strings = _strip_string_literals_preserving_lines(code_portion)

        # Import allowlist gate.
        import_match = IMPORT_RE.match(code_portion)
        if import_match:
            modules = import_match.group(1).split()
            for module in modules:
                if not _module_allowed(module, cfg.profile):
                    errors.append(
                        f"Line {line_no}: import `{module}` is not allowlisted for Profile {cfg.profile}."
                    )

        # set_option allowlist gate.
        option_match = SET_OPTION_RE.match(code_portion)
        if option_match:
            option_name = option_match.group(1)
            if option_name not in ALLOWED_SET_OPTIONS:
                errors.append(
                    f"Line {line_no}: set_option `{option_name}` is not allowlisted."
                )

        # Reject banned declaration keywords.
        decl_match = DECL_KEYWORD_RE.search(code_without_strings)
        if decl_match:
            keyword = decl_match.group(1)
            errors.append(f"Line {line_no}: banned keyword `{keyword}` found in checker code.")

        # Reject disallowed placeholders.
        placeholder_match = PLACEHOLDER_KEYWORD_RE.search(code_without_strings)
        if placeholder_match:
            keyword = placeholder_match.group(1)
            errors.append(f"Line {line_no}: disallowed placeholder `{keyword}` found in checker code.")

        sanitized_lines.append(sanitized_line)

    if cfg.profile not in {"A", "B"}:
        errors.append(f"Unsupported sanitizer profile `{cfg.profile}`.")

    sanitized_source = "\n".join(sanitized_lines)
    for residual in _find_residual_banned_attributes(sanitized_source):
        errors.append(
            f"Line {residual.line_no}: banned attribute `@[{residual.attribute}]` not removed."
        )
    if cfg.enforce_template_contract:
        errors.extend(_validate_template_contract(sanitized_source))

    return SanitizationResult(
        sanitized_source=sanitized_source,
        errors=errors,
        warnings=warnings,
        stripped_attributes=stripped_attributes,
    )


def sanitize_artifact_dict(
    artifact_data: dict[str, Any], config: SanitizerConfig | None = None
) -> SanitizationResult:
    cfg = config or SanitizerConfig()
    ok_schema, schema_errors = validate_artifact_schema(artifact_data, strict=cfg.strict_schema)
    if not ok_schema:
        return SanitizationResult(sanitized_source="", errors=schema_errors)

    artifact = LeanCheckerArtifact(
        schema_version=artifact_data["schema_version"],
        profile=artifact_data["profile"],
        source=artifact_data["source"],
        metadata=artifact_data.get("metadata", {}),
    )
    source_result = sanitize_source(
        artifact.source,
        SanitizerConfig(profile=artifact.profile, strict_schema=cfg.strict_schema),
    )
    if schema_errors:
        source_result.errors.extend(schema_errors)
    return source_result


def _strip_banned_attributes(source: str, stripped_attributes: list[str]) -> str:
    def replace(match: re.Match[str]) -> str:
        block = match.group(0)
        attrs = [a.strip() for a in match.group(1).split(",")]
        kept: list[str] = []
        for attr in attrs:
            normalized = attr.lstrip("@")
            attr_head = normalized.split()[0] if normalized else ""
            attr_key = _canonical_attribute_name(attr_head)
            if attr_key in BANNED_ATTRIBUTES:
                stripped_attributes.append(attr_key)
            elif normalized:
                kept.append(normalized)
        if not kept:
            return "\n" * block.count("\n")
        replacement = "@[" + ", ".join(kept) + "]"
        newline_delta = block.count("\n") - replacement.count("\n")
        if newline_delta > 0:
            replacement += "\n" * newline_delta
        return replacement

    return ATTRIBUTE_BLOCK_RE.sub(replace, source)


@dataclass(slots=True)
class _ResidualAttribute:
    line_no: int
    attribute: str


def _find_residual_banned_attributes(source: str) -> list[_ResidualAttribute]:
    residuals: list[_ResidualAttribute] = []
    code_only = _strip_comments_preserving_lines(source)
    code_only = _strip_string_literals_preserving_lines(code_only)
    for match in ATTRIBUTE_BLOCK_RE.finditer(code_only):
        attrs = [a.strip() for a in match.group(1).split(",")]
        line_no = code_only.count("\n", 0, match.start()) + 1
        for attr in attrs:
            normalized = attr.lstrip("@")
            attr_head = normalized.split()[0] if normalized else ""
            attr_key = _canonical_attribute_name(attr_head)
            if attr_key in BANNED_ATTRIBUTES:
                residuals.append(_ResidualAttribute(line_no=line_no, attribute=attr_key))
    return residuals


def _canonical_attribute_name(name: str) -> str:
    token = name.strip()
    if not token:
        return ""
    token = token.lstrip("@")
    if token.startswith("_root_."):
        token = token[len("_root_.") :]
    if "." in token:
        token = token.rsplit(".", 1)[-1]
    return token


def _module_allowed(module: str, profile: str) -> bool:
    if module == "Init" or module.startswith("Init."):
        return True
    if profile == "B" and module == "Mathlib.Tactic":
        return True
    return False


def _validate_template_contract(source: str) -> list[str]:
    errors: list[str] = []
    code_only_source = _strip_comments_preserving_lines(source)
    code_only_no_strings = _strip_string_literals_preserving_lines(code_only_source)
    if re.search(r"^\s*#", code_only_no_strings, re.MULTILINE):
        errors.append("Template contract violation: command directives are disallowed.")
    if re.search(r"\bdef\s+expected\s*:\s*Array\s+Nat\s*:=\s*#\[\s*\]", code_only_source):
        errors.append("Template contract violation: expected observations cannot be empty.")

    for name, pattern in REQUIRED_TEMPLATE_PATTERNS:
        if pattern.search(code_only_source) is None:
            errors.append(f"Template contract violation: missing `{name}`.")

    expected_type_pattern = re.compile(r"^\s*def\s+expected\s*:\s*Array\b", re.MULTILINE)
    if expected_type_pattern.search(code_only_source) is None:
        errors.append("Template contract violation: `expected` must be typed as `Array`.")

    for match in PLACEHOLDER_KEYWORD_RE.finditer(code_only_no_strings):
        keyword = match.group(1)
        if keyword in DISALLOWED_PROOF_PLACEHOLDERS:
            errors.append(
                f"Template contract violation: disallowed placeholder `{keyword}` found."
            )
            break

    verify_block = _extract_verify_theorem_block(code_only_source)
    if verify_block is not None:
        verify_statement, proof_body = _split_verify_theorem_parts(verify_block)
        tactic = _detect_verify_tactic(proof_body)
        if tactic is None:
            errors.append(
                "Template contract violation: `theorem verify` must use `native_decide` or `grind`."
            )
        else:
            normalized_statement = _normalize_space(verify_statement)
            if normalized_statement == "True":
                errors.append(
                    "Template contract violation: `theorem verify` statement cannot be `True`."
                )
            if tactic == "native_decide" and not _native_verify_statement_allowed(verify_statement):
                errors.append(
                    "Template contract violation: `native_decide` verify theorem must prove formula-vs-expected equality."
                )
            if tactic == "grind" and ("f" not in normalized_statement and "expected" not in normalized_statement):
                errors.append(
                    "Template contract violation: `grind` verify theorem must reference `f` or `expected`."
                )

    return errors


def _strip_comments_preserving_lines(source: str) -> str:
    """Strip Lean comments while respecting string literals and preserving line boundaries."""
    out: list[str] = []
    depth = 0
    in_string = False
    escaped = False
    i = 0
    while i < len(source):
        ch = source[i]
        if depth > 0:
            if source.startswith("/-", i):
                depth += 1
                out.extend("  ")
                i += 2
                continue
            if source.startswith("-/", i):
                depth -= 1
                out.extend("  ")
                i += 2
                continue
            if ch == "\n":
                out.append("\n")
            else:
                out.append(" ")
            i += 1
            continue

        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if source.startswith("--", i):
            out.extend("  ")
            i += 2
            while i < len(source) and source[i] != "\n":
                out.append(" ")
                i += 1
            continue

        if source.startswith("/-", i):
            depth += 1
            out.extend("  ")
            i += 2
            continue

        if ch == '"':
            in_string = True
            escaped = False

        out.append(ch)
        i += 1

    return "".join(out)


def _strip_string_literals_preserving_lines(source: str) -> str:
    out: list[str] = []
    in_string = False
    escaped = False
    for ch in source:
        if in_string:
            if ch == "\n":
                out.append("\n")
                escaped = False
                continue
            out.append(" ")
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            escaped = False
            out.append(" ")
            continue
        out.append(ch)
    return "".join(out)


def _extract_verify_theorem_block(source: str) -> str | None:
    lines = source.splitlines()
    start_idx: int | None = None
    for idx, line in enumerate(lines):
        if VERIFY_THEOREM_RE.match(line):
            start_idx = idx
            break

    if start_idx is None:
        return None

    block_lines: list[str] = [lines[start_idx]]
    for line in lines[start_idx + 1 :]:
        stripped = line.strip()
        if stripped and not line[0].isspace() and TOP_LEVEL_DECL_RE.match(stripped):
            break
        block_lines.append(line)

    return "\n".join(block_lines)


def _split_verify_theorem_parts(verify_block: str) -> tuple[str, str]:
    header, *body_lines = verify_block.splitlines()
    full_header = header
    remaining = body_lines[:]

    if ":= by" not in full_header:
        while remaining:
            next_line = remaining.pop(0)
            full_header += "\n" + next_line
            if ":= by" in full_header:
                break

    match = VERIFY_HEADER_RE.match(full_header)
    if match is None:
        return "", verify_block
    statement = match.group("statement").strip()
    proof_body = "\n".join(remaining)
    return statement, proof_body


def _detect_verify_tactic(proof_body: str) -> str | None:
    sanitized = STRING_LITERAL_RE.sub('""', proof_body)
    tokens = TACTIC_TOKEN_RE.findall(sanitized)
    if not tokens:
        return None
    for token in tokens:
        if token == "native_decide":
            return "native_decide"
    for token in tokens:
        if token == "grind":
            return "grind"
    return None


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _native_verify_statement_allowed(statement: str) -> bool:
    unwrapped = _strip_outer_parens(statement.strip())
    return _canonicalize_lean_expr(unwrapped) == _canonicalize_lean_expr(NATIVE_VERIFY_SHAPE_EXACT)


def _canonicalize_lean_expr(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _strip_outer_parens(text: str) -> str:
    out = text
    while out.startswith("(") and out.endswith(")") and _outer_parens_wrap_entire_expr(out):
        out = out[1:-1].strip()
    return out


def _outer_parens_wrap_entire_expr(text: str) -> bool:
    depth = 0
    for index, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
            if depth == 0 and index != len(text) - 1:
                return False
    return depth == 0


sanitize_lean_source = sanitize_source
