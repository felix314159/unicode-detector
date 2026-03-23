#!/usr/bin/env python3
"""Compatibility wrapper for the published ``unicode-detector`` CLI."""

if __name__ == "__main__":
    from unicode_detector.cli import main

    raise SystemExit(main())
