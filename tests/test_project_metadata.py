from __future__ import annotations

from pathlib import Path
import tomllib

import lean_kernel_verifier


def test_supported_python_range_matches_runtime_features() -> None:
    project_root = Path(__file__).resolve().parents[1]
    with (project_root / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)["project"]

    assert project["version"] == lean_kernel_verifier.__version__ == "0.3.2"
    assert project["requires-python"] == ">=3.11,<3.14"
    assert "Programming Language :: Python :: 3.10" not in project["classifiers"]
    assert "Programming Language :: Python :: 3.13" in project["classifiers"]
