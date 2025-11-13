"""Top-level command wiring."""

from __future__ import annotations

import argparse

from . import deploy as deploy_cmd
from . import destroy as destroy_cmd
from . import init as init_cmd
from . import status as status_cmd
from . import templates


def register_ai_plugin(subparsers: argparse._SubParsersAction, config) -> None:
    """Register the `ai` command namespace for the main CLI."""
    ai_parser = subparsers.add_parser(
        "ai",
        help="Deploy AI demo applications on Linode",
    )
    ai_parser.set_defaults(func=lambda args: ai_parser.print_help())
    ai_subparsers = ai_parser.add_subparsers(dest="ai_command")
    _register_subcommands(ai_subparsers, config)


def register_root_parser(parser: argparse.ArgumentParser, config) -> None:
    """Register subcommands when running as a standalone plugin."""
    parser.set_defaults(func=lambda args: parser.print_help())
    subparsers = parser.add_subparsers(dest="ai_command")
    _register_subcommands(subparsers, config)


def _register_subcommands(subparsers: argparse._SubParsersAction, config) -> None:
    templates.register(subparsers, config)
    init_cmd.register(subparsers, config)
    deploy_cmd.register(subparsers, config)
    status_cmd.register(subparsers, config)
    destroy_cmd.register(subparsers, config)
