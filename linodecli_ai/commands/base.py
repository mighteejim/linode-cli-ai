"""Top-level command wiring."""

from __future__ import annotations

import argparse

from . import deploy as deploy_cmd
from . import destroy as destroy_cmd
from . import init as init_cmd
from . import status as status_cmd
from . import templates


def register_ai_plugin(subparsers: argparse._SubParsersAction, config) -> None:
    """Register the `ai` command namespace."""
    ai_parser = subparsers.add_parser(
        "ai",
        help="Deploy AI demo applications on Linode",
    )
    ai_parser.set_defaults(func=lambda args: ai_parser.print_help())
    ai_subparsers = ai_parser.add_subparsers(dest="ai_command")

    templates.register(ai_subparsers, config)
    init_cmd.register(ai_subparsers, config)
    deploy_cmd.register(ai_subparsers, config)
    status_cmd.register(ai_subparsers, config)
    destroy_cmd.register(ai_subparsers, config)
