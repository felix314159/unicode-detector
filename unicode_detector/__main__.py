"""Module entrypoint for ``python -m unicode_detector``."""

if __name__ == "__main__":
    from unicode_detector.cli import main

    raise SystemExit(main())
