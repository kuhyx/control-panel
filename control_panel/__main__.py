"""Allow ``python -m control_panel``."""

from control_panel._cli import main

if __name__ == "__main__":
    raise SystemExit(main())
