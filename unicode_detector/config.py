"""Configuration loading for unicode-detector."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_IGNORED_DIRS: tuple[str, ...] = ()
DEFAULT_IGNORED_FILETYPES: tuple[str, ...] = ()
DEFAULT_WHITELISTED_UNICODE_CHARS: tuple[str, ...] = ()
DEFAULT_COMMON_UNICODE_THRESHOLD = 5


@dataclass(frozen=True)
class DetectorConfig:
    """Configuration values that control scanning behavior."""

    ignored_dirs: tuple[str, ...] = DEFAULT_IGNORED_DIRS
    ignored_filetypes: tuple[str, ...] = DEFAULT_IGNORED_FILETYPES
    whitelisted_unicode_chars: tuple[str, ...] = (
        DEFAULT_WHITELISTED_UNICODE_CHARS
    )
    common_unicode_threshold: int = DEFAULT_COMMON_UNICODE_THRESHOLD


def discover_pyproject(start_dir: Path) -> Path | None:
    """Find the nearest ``pyproject.toml`` from ``start_dir`` upward."""
    for directory in (start_dir, *start_dir.parents):
        candidate = directory / "pyproject.toml"
        if candidate.is_file():
            return candidate
    return None


def _coerce_string_list(value: Any, *, field_name: str) -> tuple[str, ...]:
    """Validate a sequence of strings from config."""
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list of strings")
    if not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} must be a list of strings")
    return tuple(value)


def _normalize_filetypes(filetypes: tuple[str, ...]) -> tuple[str, ...]:
    """Normalize configured filetype suffixes."""
    normalized: list[str] = []
    for filetype in filetypes:
        suffix = filetype if filetype.startswith(".") else f".{filetype}"
        normalized.append(suffix.lower())
    return tuple(dict.fromkeys(normalized))


def _coerce_threshold(value: Any) -> int:
    """Validate the common-char reporting threshold."""
    if value is None:
        return DEFAULT_COMMON_UNICODE_THRESHOLD
    if not isinstance(value, int):
        raise ValueError("common_unicode_threshold must be an integer")
    if value < 1:
        raise ValueError("common_unicode_threshold must be at least 1")
    return value


def build_config(raw_config: dict[str, Any]) -> DetectorConfig:
    """Build a validated configuration from a mapping."""
    ignored_dirs = _coerce_string_list(
        raw_config.get("ignored_dirs"),
        field_name="ignored_dirs",
    )
    ignored_filetypes = _normalize_filetypes(
        _coerce_string_list(
            raw_config.get("ignored_filetypes"),
            field_name="ignored_filetypes",
        )
    )
    whitelisted_unicode_chars = _coerce_string_list(
        raw_config.get("whitelisted_unicode_chars"),
        field_name="whitelisted_unicode_chars",
    )
    common_unicode_threshold = _coerce_threshold(
        raw_config.get("common_unicode_threshold")
    )

    base_config = DetectorConfig()
    return DetectorConfig(
        ignored_dirs=ignored_dirs or base_config.ignored_dirs,
        ignored_filetypes=ignored_filetypes or base_config.ignored_filetypes,
        whitelisted_unicode_chars=(
            whitelisted_unicode_chars
            or base_config.whitelisted_unicode_chars
        ),
        common_unicode_threshold=common_unicode_threshold,
    )


def _read_toml(path: Path) -> dict[str, Any]:
    """Read a TOML file into a dictionary."""
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _extract_config_mapping(path: Path) -> dict[str, Any]:
    """Extract config data from a dedicated TOML file or ``pyproject.toml``."""
    data = _read_toml(path)
    tool_config = (
        data.get("tool", {}).get("unicode-detector")
        if isinstance(data.get("tool"), dict)
        else None
    )

    if path.name == "pyproject.toml":
        return tool_config if isinstance(tool_config, dict) else {}
    if isinstance(tool_config, dict):
        return tool_config
    return data


def load_config(
    config_path: str | None,
    *,
    start_dir: Path,
) -> tuple[DetectorConfig, Path | None]:
    """Load config from ``--config`` or nearest ``pyproject.toml``."""
    resolved_path: Path | None
    if config_path:
        resolved_path = Path(config_path).expanduser().resolve()
        if not resolved_path.is_file():
            raise FileNotFoundError(
                f"config file does not exist: {resolved_path}"
            )
    else:
        resolved_path = discover_pyproject(start_dir)

    if resolved_path is None:
        return DetectorConfig(), None

    return build_config(_extract_config_mapping(resolved_path)), resolved_path
