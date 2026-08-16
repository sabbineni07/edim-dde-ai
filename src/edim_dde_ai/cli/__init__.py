"""Command-line interface.

Business purpose:
  Expose ``edim-dde-ai`` / ``python -m edim_dde_ai`` for register/list/run/validate.

Public API:
  - ``main`` — argparse entrypoint returning a process exit code
"""

from edim_dde_ai.cli.main import main

__all__ = ["main"]
