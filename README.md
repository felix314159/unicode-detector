# unicode-detector

`unicode-detector` is a small Python CLI for finding non-whitelisted Unicode
characters in text files. It is designed to work well in local development,
CI, and GitHub Actions workflows that only scan changed files.

## Why Scan Unicode

Unicode can hide dangerous content in code and documentation changes that look
harmless in reviews. Invisible characters can be used for LLM prompt-injection
payloads, obfuscated code execution tricks, or other attacks that arrive in a
seemingly innocent "fix typo" pull request.

For example, this Python snippet contains an invisible Unicode payload that
just prints `hello world`, but the same technique could hide something
malicious:

```python
fav_number = 8203
l = {chr(fav_number): "0", chr(fav_number + 1): "1"}
not_empty = "​‌‌​‌​​​​‌‌​​‌​‌​‌‌​‌‌​​​‌‌​‌‌​​​‌‌​‌‌‌‌​​‌​​​​​​‌‌‌​‌‌‌​‌‌​‌‌‌‌​‌‌‌​​‌​​‌‌​‌‌​​​‌‌​​‌​​"

bits = "".join(l[ol] for ol in not_empty)
print(bytes(int(bits[i : i + 8], 2) for i in range(0, len(bits), 8)).decode())
```

## Install

Use it directly with `uvx` once it is published:

```bash
uvx unicode-detector --help
```

For local development in this repo:

```bash
uv run unicode-detector --help
```

## Usage

Scan the current directory recursively:

```bash
uv run unicode-detector
```

Scan a single file or directory:

```bash
uv run unicode-detector path/to/file.py
uv run unicode-detector path/to/directory
```

Scan only changed files from a newline-delimited list:

```bash
uv run unicode-detector --files-from changed_files.txt
```

Scan files piped from standard input:

```bash
git diff --name-only --diff-filter=AMR HEAD~1 HEAD | \
  uv run unicode-detector --files-from -
```

Emit machine-readable JSON:

```bash
uv run unicode-detector --format json
```

## Configuration

By default the CLI searches upward for the nearest `pyproject.toml` and reads
`[tool.unicode-detector]`.

You can also point it at a dedicated TOML file:

```bash
uv run unicode-detector --config unicode-detector.toml
```

Supported config keys:

- `ignored_dirs`
- `ignored_filetypes`
- `whitelisted_unicode_chars`
- `common_unicode_threshold` (cosmetic setting that affects only logging)

By default, `unicode-detector` is strict:

- no ignored directories
- no ignored filetypes
- no whitelisted Unicode characters

Example `pyproject.toml` for a less strict setup:

```toml
[tool.unicode-detector]
ignored_dirs = [
  ".git",
  ".venv",
  ".vscode",
  "venv",
  "__pycache__",
  ".mypy_cache",
  ".pytest_cache",
  ".ruff_cache",
  ".tox",
  "node_modules",
  "dist",
  "build",
  "fixtures",
  "logs",
]
ignored_filetypes = []
whitelisted_unicode_chars = [
  "✅",
  "❌",
  "🔥",
  "💥",
  "🚀",
  "❓",
  "🤝",
  "🔗",
  "🚨",
  "💡",
  "🛠",
  "✨",
  "🐞",
  "🔁",
  "🔀",
  "📄",
  "📁",
  "📂",
  "🟢",
  "🟡",
  "🔴",
  "🎉",
  "🧪",
  "📋",
  "🐍",
  "🐘",
  "🗑",
  "⚠",
  "►",
  "→",
  "✓",
  "✗",
  "┌",
  "┬",
  "┘",
  "├",
  "┤",
  "┼",
  "│",
  "┴",
  "└",
  "┐",
  "╔",
  "╗",
  "╚",
  "╝",
  "±",
  "²",
  "³",
  "≡",
  "═",
  "≤",
  "≥",
  "≠",
  "≈",
  "─",
  "—",
  "ł",
  "’",
  "\u00a0",
]
common_unicode_threshold = 5
```

See [examples/pyproject.toml](examples/pyproject.toml)
for a copy-pasteable less strict example.

## GitHub Actions

### Minimal workflow for another repository

```yaml
- uses: actions/checkout@v4
- uses: astral-sh/setup-uv@v7
- name: Collect changed files
  run: git diff --name-only --diff-filter=AMR "$BASE_SHA" "$HEAD_SHA" > changed_files.txt
- name: Run unicode-detector
  run: uvx unicode-detector --files-from changed_files.txt
```

### Reusable workflow for another repository

To avoid copying the changed-file logic, another repository can call the
reusable workflow published by this repo:

```yaml
name: Unicode Detector

on:
  pull_request:
    types: [opened, reopened, synchronize]

permissions:
  contents: read

jobs:
  unicode-detector:
    uses: felix314159/unicode-detector/.github/workflows/reusable-unicode-detector.yaml@main
```

Optional inputs:

```yaml
jobs:
  unicode-detector:
    uses: felix314159/unicode-detector/.github/workflows/reusable-unicode-detector.yaml@main
    with:
      config-path: pyproject.toml
      root: .
      format: text
```

For stability, consumers can pin to a release tag or commit SHA instead of
`@main`.

To block merging until the check passes, the consuming repository must also
mark the `unicode-detector` status check as required in branch protection or
its ruleset.

### This repository's PR workflow

This repo includes
[.github/workflows/unicode-detector.yaml](.github/workflows/unicode-detector.yaml),
which scans the full current PR diff on `pull_request` `opened`,
`reopened`, and `synchronize`.

## Release process

- Run `uv run python scripts/bump_version.py patch`
- Update [CHANGELOG.md](CHANGELOG.md)
- Commit the version bump
- Create a Git tag such as `v0.1.3`
- Push the tag to trigger the PyPI publish workflow

## Development

Run local checks with:

```bash
uv run ruff check .
uv run mypy
uv run pytest
```
