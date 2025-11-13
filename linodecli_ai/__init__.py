"""`linode-cli ai` plugin entrypoint."""

from __future__ import annotations

import argparse

from linodecli.plugins import plugins as plugin_core

from .commands import base

PLUGIN_NAME = "ai"
PLUGIN_DESCRIPTION = "Deploy AI demo applications on Linode."
PLUGIN_AUTHOR = "Linode"
PLUGIN_VERSION = "0.1.0"


def call(args, context):
    """Entrypoint invoked by linode-cli when running `linode-cli ai`."""
    parser = argparse.ArgumentParser(prog="linode-cli ai")
    plugin_core.inherit_plugin_args(parser)
    subparsers = parser.add_subparsers(dest="command")

    base.register_ai_plugin(subparsers, context)

    parsed_args = parser.parse_args(args)
    func = getattr(parsed_args, "func", None)
    if func is None:
        parser.print_help()
        return
    func(parsed_args)


def populate(subparsers, config):
    """Compatibility helper for the Core CLI to reuse command wiring."""
    base.register_ai_plugin(subparsers, config)
