"""Tests for configuration loading."""

from __future__ import annotations

from pathlib import Path

from unicode_detector.config import load_config


def test_load_config_from_pyproject(tmp_path: Path) -> None:
    """The nearest pyproject config should be discovered automatically."""
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.unicode-detector]
ignored_dirs = ["custom-build"]
ignored_filetypes = [".png"]
whitelisted_unicode_chars = ["║"]
common_unicode_threshold = 9
""".strip(),
        encoding="utf-8",
    )

    config, config_path = load_config(None, start_dir=tmp_path)

    assert config_path == tmp_path / "pyproject.toml"
    assert config.ignored_dirs == ("custom-build",)
    assert config.ignored_filetypes == (".png",)
    assert config.whitelisted_unicode_chars == ("║",)
    assert config.common_unicode_threshold == 9


def test_load_config_from_explicit_toml(tmp_path: Path) -> None:
    """A dedicated config file should load without a tool section."""
    config_file = tmp_path / "unicode-detector.toml"
    config_file.write_text(
        """
ignored_dirs = ["output"]
ignored_filetypes = ["svg"]
whitelisted_unicode_chars = ["→"]
common_unicode_threshold = 7
""".strip(),
        encoding="utf-8",
    )

    config, config_path = load_config(str(config_file), start_dir=tmp_path)

    assert config_path == config_file
    assert config.ignored_dirs == ("output",)
    assert config.ignored_filetypes == (".svg",)
    assert config.whitelisted_unicode_chars == ("→",)
    assert config.common_unicode_threshold == 7
