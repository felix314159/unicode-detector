"""Core scanning logic for unicode-detector."""

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from unicode_detector.config import DetectorConfig


@dataclass(frozen=True)
class Finding:
    """One disallowed Unicode character occurrence."""

    path: Path
    lineno: int
    colno: int
    char: str
    codepoint: str

    @property
    def detail_text(self) -> str:
        """Return the detailed finding line for text output."""
        return (
            f"{self.path}:{self.lineno}:{self.colno}:"
            f" {self.char!r} ({self.codepoint})"
        )

    @property
    def summary_text(self) -> str:
        """Return the summary finding line for text output."""
        return (
            f"{self.path}:{self.lineno} {self.char!r}"
            f" ({self.codepoint}) not allowed"
        )

    def to_json(self) -> dict[str, object]:
        """Return a JSON-serializable representation of the finding."""
        return {
            "path": str(self.path),
            "lineno": self.lineno,
            "colno": self.colno,
            "char": self.char,
            "codepoint": self.codepoint,
        }


@dataclass
class ScanResult:
    """Aggregated scanner output."""

    scanned_files: int = 0
    findings: list[Finding] = field(default_factory=list)
    files_with_findings: set[Path] = field(default_factory=set)
    char_counts: Counter[str] = field(default_factory=Counter)
    elapsed_seconds: float = 0.0

    @property
    def total_findings(self) -> int:
        """Return the total number of findings."""
        return len(self.findings)

    def common_chars(self, threshold: int) -> list[tuple[str, int]]:
        """Return frequent disallowed characters at or above ``threshold``."""
        return [
            (char, count)
            for char, count in sorted(
                self.char_counts.items(),
                key=lambda item: (-item[1], ord(item[0])),
            )
            if count >= threshold
        ]

    def to_json(self, threshold: int) -> dict[str, object]:
        """Return a JSON-serializable representation of the full scan."""
        return {
            "scanned_files": self.scanned_files,
            "total_findings": self.total_findings,
            "files_with_findings": [
                str(path) for path in sorted(self.files_with_findings)
            ],
            "elapsed_seconds": round(self.elapsed_seconds, 6),
            "common_chars": [
                {
                    "char": char,
                    "codepoint": f"U+{ord(char):04X}",
                    "count": count,
                }
                for char, count in self.common_chars(threshold)
            ],
            "findings": [finding.to_json() for finding in self.findings],
        }


def resolve_target_path(target: str, *, base_dir: Path) -> Path:
    """Resolve a target path relative to ``base_dir``."""
    path = Path(target)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    else:
        path = path.resolve()
    return path


def load_paths_from_file(files_from: str | None) -> list[str]:
    """Load newline-delimited scan paths from a file or standard input."""
    if not files_from:
        return []

    if files_from == "-":
        content = sys.stdin.read()
    else:
        content = Path(files_from).read_text(encoding="utf-8")

    return [line for line in content.splitlines() if line]


def normalize_ignore_paths(
    root: Path,
    ignored_dirs: tuple[str, ...],
) -> set[Path]:
    """Resolve ignored directory entries relative to the scan root."""
    ignored: set[Path] = set()
    for entry in ignored_dirs:
        path = Path(entry)
        if not path.is_absolute():
            path = (root / path).resolve()
        else:
            path = path.resolve()
        ignored.add(path)
    return ignored


def is_ignored_path(path: Path, ignored_paths: set[Path]) -> bool:
    """Return whether a path should be skipped entirely."""
    for ignored in ignored_paths:
        if path == ignored or ignored in path.parents:
            return True
    return False


def is_ignored_filetype(
    path: Path,
    ignored_filetypes: tuple[str, ...],
) -> bool:
    """Return whether a path has an ignored suffix."""
    return path.suffix.lower() in ignored_filetypes


def is_binary_file(path: Path) -> bool:
    """Best-effort check for binary files based on NUL bytes."""
    try:
        with path.open("rb") as file:
            chunk = file.read(4096)
        return b"\x00" in chunk
    except OSError:
        return True


def scan_file(
    path: Path,
    *,
    whitelisted_chars: set[str],
) -> list[Finding]:
    """Collect disallowed Unicode findings for one file."""
    findings: list[Finding] = []

    try:
        with path.open("r", encoding="utf-8", errors="replace") as file:
            for lineno, line in enumerate(file, 1):
                if line.isascii():
                    continue

                for colno, char in enumerate(line, 1):
                    if ord(char) > 127 and char not in whitelisted_chars:
                        findings.append(
                            Finding(
                                path=path,
                                lineno=lineno,
                                colno=colno,
                                char=char,
                                codepoint=f"U+{ord(char):04X}",
                            )
                        )
    except OSError as error:
        print(f"ERROR reading {path}: {error}", file=sys.stderr)

    return findings


def iter_files(
    root: Path,
    *,
    ignored_paths: set[Path],
    ignored_filetypes: tuple[str, ...],
) -> Iterator[Path]:
    """Yield non-ignored, non-binary files beneath ``root``."""
    for dirpath, dirnames, filenames in os.walk(root):
        current_dir = Path(dirpath).resolve()

        dirnames[:] = sorted(
            directory
            for directory in dirnames
            if not is_ignored_path(current_dir / directory, ignored_paths)
        )

        for filename in sorted(filenames):
            path = current_dir / filename
            if is_ignored_path(path, ignored_paths):
                continue
            if is_ignored_filetype(path, ignored_filetypes):
                continue
            if is_binary_file(path):
                continue
            yield path


def iter_scan_paths(
    targets: Iterable[str],
    *,
    base_dir: Path,
    ignored_paths: set[Path],
    ignored_filetypes: tuple[str, ...],
) -> Iterator[Path]:
    """Yield unique file paths from explicit file or directory targets."""
    seen_paths: set[Path] = set()

    for target in targets:
        path = resolve_target_path(target, base_dir=base_dir)
        if not path.exists():
            continue
        if is_ignored_path(path, ignored_paths):
            continue

        if path.is_dir():
            for nested_path in iter_files(
                path,
                ignored_paths=ignored_paths,
                ignored_filetypes=ignored_filetypes,
            ):
                if nested_path not in seen_paths:
                    seen_paths.add(nested_path)
                    yield nested_path
            continue

        if (
            is_ignored_filetype(path, ignored_filetypes)
            or is_binary_file(path)
        ):
            continue
        if path not in seen_paths:
            seen_paths.add(path)
            yield path


def scan_paths(
    paths: Iterable[Path],
    *,
    config: DetectorConfig,
) -> ScanResult:
    """Scan a sequence of file paths and collect result data."""
    start_time = time.perf_counter()
    result = ScanResult()
    whitelisted_chars = set(config.whitelisted_unicode_chars)

    for path in paths:
        result.scanned_files += 1
        file_findings = scan_file(path, whitelisted_chars=whitelisted_chars)
        if not file_findings:
            continue

        result.files_with_findings.add(path)
        result.findings.extend(file_findings)
        for finding in file_findings:
            result.char_counts[finding.char] += 1

    result.elapsed_seconds = time.perf_counter() - start_time
    return result


def format_text(result: ScanResult, *, threshold: int) -> str:
    """Render a scan result as human-readable text."""
    lines = [finding.detail_text for finding in result.findings]
    lines.append("")
    lines.append(
        "Summary:"
        f" {result.total_findings} non-whitelisted unicode character"
        f"{'' if result.total_findings == 1 else 's'} found in"
        f" {len(result.files_with_findings)} file"
        f"{'' if len(result.files_with_findings) == 1 else 's'}."
    )
    lines.append(
        f"Scanned {result.scanned_files} file"
        f"{'' if result.scanned_files == 1 else 's'} in"
        f" {result.elapsed_seconds:.3f} seconds."
    )

    common_chars = result.common_chars(threshold)
    if common_chars:
        lines.append(
            "Most common unicode chars "
            f"(minimum {threshold} occurrences):"
        )
        for char, count in common_chars:
            lines.append(f"  U+{ord(char):04X} {char!r}: {count}")

    if result.findings:
        lines.append("")
        lines.append("Errors:")
        for finding in result.findings:
            lines.append(f"  {finding.summary_text}")

    return "\n".join(lines)


def format_json(result: ScanResult, *, threshold: int) -> str:
    """Render a scan result as JSON."""
    return json.dumps(
        result.to_json(threshold),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
