"""Command-line interface for unicode-detector."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from unicode_detector import __version__
from unicode_detector.config import DetectorConfig, load_config
from unicode_detector.scanner import (
    format_json,
    format_text,
    iter_files,
    iter_scan_paths,
    load_paths_from_file,
    normalize_ignore_paths,
    resolve_target_path,
    scan_paths,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Find non-whitelisted Unicode characters in text files."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Paths to scan. Defaults to the current directory.",
    )
    parser.add_argument(
        "--files-from",
        help=(
            "Read newline-delimited paths to scan from a file, "
            "or '-' for stdin."
        ),
    )
    parser.add_argument(
        "--config",
        help=(
            "Read configuration from a TOML file. If omitted, the nearest "
            "pyproject.toml is searched for [tool.unicode-detector]."
        ),
    )
    parser.add_argument(
        "--root",
        help=(
            "Base directory for resolving relative scan targets and "
            "relative ignored directories."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format. Defaults to text.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser.parse_args()


def determine_scan_root(
    args: argparse.Namespace,
    requested_targets: list[str],
) -> Path:
    """Determine the scan root for config discovery and relative paths."""
    if args.root:
        return Path(args.root).expanduser().resolve()
    if not requested_targets:
        return Path.cwd().resolve()
    if args.files_from or len(args.paths) > 1:
        return Path.cwd().resolve()

    resolved = resolve_target_path(requested_targets[0], base_dir=Path.cwd())
    return resolved if resolved.is_dir() else resolved.parent


def validate_single_target(
    args: argparse.Namespace,
    requested_targets: list[str],
    *,
    scan_root: Path,
) -> int | None:
    """Return an exit code if a single explicit target is invalid."""
    if args.files_from or len(requested_targets) != 1:
        return None

    base_dir = scan_root if args.root else Path.cwd().resolve()
    resolved = resolve_target_path(requested_targets[0], base_dir=base_dir)
    if resolved.exists():
        return None

    print(f"ERROR: path does not exist: {resolved}", file=sys.stderr)
    return 2


def build_target_iterator(
    args: argparse.Namespace,
    requested_targets: list[str],
    *,
    scan_root: Path,
    config: DetectorConfig,
):
    """Build the iterator of files that should be scanned."""
    ignored_paths = normalize_ignore_paths(scan_root, config.ignored_dirs)

    if not requested_targets:
        requested_targets = [str(scan_root)]

    if args.files_from or len(requested_targets) > 1:
        return iter_scan_paths(
            requested_targets,
            base_dir=scan_root,
            ignored_paths=ignored_paths,
            ignored_filetypes=config.ignored_filetypes,
        )

    single_target_base_dir = scan_root if args.root else Path.cwd().resolve()
    only_target = resolve_target_path(
        requested_targets[0],
        base_dir=single_target_base_dir,
    )
    if only_target.is_dir():
        return iter_files(
            only_target,
            ignored_paths=ignored_paths,
            ignored_filetypes=config.ignored_filetypes,
        )
    return iter_scan_paths(
        [str(only_target)],
        base_dir=scan_root,
        ignored_paths=ignored_paths,
        ignored_filetypes=config.ignored_filetypes,
    )


def main() -> int:
    """Run the Unicode scan and report findings."""
    args = parse_args()
    requested_targets = [*args.paths, *load_paths_from_file(args.files_from)]
    scan_root = determine_scan_root(args, requested_targets)

    single_target_status = validate_single_target(
        args,
        requested_targets,
        scan_root=scan_root,
    )
    if single_target_status is not None:
        return single_target_status

    try:
        config, _ = load_config(args.config, start_dir=scan_root)
    except (FileNotFoundError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    result = scan_paths(
        build_target_iterator(
            args,
            requested_targets,
            scan_root=scan_root,
            config=config,
        ),
        config=config,
    )

    if args.format == "json":
        print(format_json(result, threshold=config.common_unicode_threshold))
    else:
        print(format_text(result, threshold=config.common_unicode_threshold))

    return 1 if result.total_findings else 0
