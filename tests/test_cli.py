"""CLI-level tests for unicode-detector."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_cli(*args: str, cwd: Path, input_text: str | None = None):
    """Run the unicode-detector CLI in a subprocess."""
    return subprocess.run(
        [sys.executable, "-m", "unicode_detector", *args],
        cwd=cwd,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_honors_pyproject_config(tmp_path: Path) -> None:
    """Pyproject config should change scan policy."""
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.unicode-detector]
whitelisted_unicode_chars = ["é"]
""".strip(),
        encoding="utf-8",
    )
    target = tmp_path / "example.txt"
    target.write_text("Cafe: é\n", encoding="utf-8")

    completed = run_cli(str(target), cwd=tmp_path)

    assert completed.returncode == 0
    assert (
        "Summary: No forbidden unicode characters were found."
        in completed.stdout
    )


def test_cli_reads_files_from_stdin(tmp_path: Path) -> None:
    """The files-from stdin mode should scan only the listed file."""
    target = tmp_path / "example.txt"
    target.write_text("Math: π\n", encoding="utf-8")

    completed = run_cli(
        "--files-from",
        "-",
        cwd=tmp_path,
        input_text=f"{target}\n",
    )

    assert completed.returncode == 1
    assert f"{target}:1:7: 'π' (U+03C0)" in completed.stdout
    assert f"{target}:1 'π' (U+03C0) not allowed" in completed.stdout


def test_cli_json_output(tmp_path: Path) -> None:
    """JSON output should be stable and machine-readable."""
    target = tmp_path / "example.txt"
    target.write_text("Math: π\n", encoding="utf-8")

    completed = run_cli("--format", "json", str(target), cwd=tmp_path)

    assert completed.returncode == 1
    payload = json.loads(completed.stdout)
    assert payload["total_findings"] == 1
    assert payload["findings"][0]["codepoint"] == "U+03C0"
