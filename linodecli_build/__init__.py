"""`linode-cli build` plugin entrypoint."""

from __future__ import annotations

import argparse

from linodecli.plugins import plugins as plugin_core

from .commands import base

PLUGIN_NAME = "build"
PLUGIN_DESCRIPTION = "Deploy applications on Linode with declarative templates."
PLUGIN_AUTHOR = "Linode"
PLUGIN_VERSION = "0.2.0"


def call(args, context):
    """Entrypoint invoked by linode-cli when running `linode-cli build`."""
    parser = argparse.ArgumentParser(prog="linode-cli build")
    plugin_core.inherit_plugin_args(parser)
    base.register_root_parser(parser, context)

    parsed_args = parser.parse_args(args)
    func = getattr(parsed_args, "func", None)
    if func is None:
        parser.print_help()
        return
    func(parsed_args)


def populate(subparsers, config):
    """Compatibility helper for the Core CLI to reuse command wiring."""
    base.register_build_plugin(subparsers, config)
