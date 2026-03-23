# unicode-detector

`unicode-detector` is a small Python CLI for finding non-whitelisted Unicode
characters in text files. It is designed to work well in local development,
CI, and GitHub Actions workflows that only scan changed files.

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
- `common_unicode_threshold`

Example `pyproject.toml`:

```toml
[tool.unicode-detector]
ignored_dirs = [".git", ".venv", "node_modules"]
ignored_filetypes = [".png", ".svg"]
whitelisted_unicode_chars = ["→", "✓", "║"]
common_unicode_threshold = 5
```

See [examples/pyproject.toml](examples/pyproject.toml)
for a copy-pasteable example.

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

### This repository's PR workflow

This repo includes
[.github/workflows/unicode-detector.yaml](.github/workflows/unicode-detector.yaml),
which scans the full current PR diff on `pull_request` `opened`,
`reopened`, and `synchronize`.

## Release process

- Bump `unicode_detector.__version__`
- Update [CHANGELOG.md](CHANGELOG.md)
- Create a Git tag such as `v0.1.0`
- Push the tag to trigger the PyPI publish workflow

## Development

Run local checks with:

```bash
uv run ruff check .
uv run mypy
uv run pytest
```
