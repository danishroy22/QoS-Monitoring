"""Allow ``python -m backend.simulator`` to launch the CLI."""

from .cli import main

raise SystemExit(main())
