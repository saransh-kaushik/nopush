"""Allow running NoPush as a module: ``python -m nopush``."""

from __future__ import annotations

from nopush.cli.app import app

if __name__ == "__main__":
    app()
