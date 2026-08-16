"""``python -m edim_dde_ai`` module entrypoint.

Business purpose:
  Delegate to ``edim_dde_ai.cli.main`` so the package is runnable as a module.

Public API:
  - Side effect: ``raise SystemExit(main())`` when executed as ``__main__``.
"""

from edim_dde_ai.cli import main

raise SystemExit(main())
