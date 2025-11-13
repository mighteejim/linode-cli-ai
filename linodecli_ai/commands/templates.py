"""Implementation of `linode-cli ai templates` commands."""

from __future__ import annotations

import argparse
import textwrap
from typing import Sequence

from ..core import templates as template_core


def register(subparsers: argparse._SubParsersAction, _config) -> None:
    parser = subparsers.add_parser("templates", help="List and inspect AI templates")
    parser.set_defaults(func=lambda args: parser.print_help())
    templates_subparsers = parser.add_subparsers(dest="templates_cmd")

    list_parser = templates_subparsers.add_parser("list", help="List available templates")
    list_parser.set_defaults(func=_cmd_list)

    show_parser = templates_subparsers.add_parser("show", help="Show template details")
    show_parser.add_argument("name", help="Template name")
    show_parser.set_defaults(func=_cmd_show)


def _cmd_list(_args):
    records = template_core.list_template_records()
    rows = []
    for record in records:
        template = template_core.load_template(record.name)
        rows.append(
            (
                template.name,
                template.version,
                template.description.strip().replace("\n", " "),
            )
        )

    if not rows:
        print("No templates found.")
        return

    _print_table(("NAME", "VERSION", "DESCRIPTION"), rows)


def _cmd_show(args):
    template = template_core.load_template(args.name)
    linode_cfg = template.data.get("deploy", {}).get("linode", {})
    container = linode_cfg.get("container", {})
    env_cfg = template.data.get("env", {})

    print(f"Name:        {template.name}")
    print(f"Display:     {template.display_name}")
    print(f"Version:     {template.version}")
    print(f"Target:      {template.data.get('deploy', {}).get('target', 'linode')}")
    print(f"Region:      {linode_cfg.get('region_default')}")
    print(f"Linode type: {linode_cfg.get('type_default')}")
    print(f"OS image:    {linode_cfg.get('image')}")
    print("")
    print("Description:")
    print(textwrap.fill(template.description, width=80))
    print("")
    print("Container:")
    print(f"  Image:           {container.get('image')}")
    print(f"  Ports:           {container.get('external_port')} -> {container.get('internal_port')}")
    if "post_start_script" in container:
        print("  Post-start hook: provided")
    if container.get("env"):
        print("  Default Env:")
        for key, value in container["env"].items():
            print(f"    - {key}={value}")
    print("")
    print("Env requirements:")
    required = env_cfg.get("required", [])
    optional = env_cfg.get("optional", [])
    if required:
        print("  Required:")
        for item in required:
            print(f"    - {item.get('name')}: {item.get('description', '')}")
    else:
        print("  Required: none")
    if optional:
        print("  Optional:")
        for item in optional:
            print(f"    - {item.get('name')}: {item.get('description', '')}")
    else:
        print("  Optional: none")


def _print_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
    widths = [len(h) for h in headers]
    for row in rows:
        widths = [max(widths[idx], len(str(value))) for idx, value in enumerate(row)]
    header_line = "  ".join(h.ljust(widths[idx]) for idx, h in enumerate(headers))
    print(header_line)
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(str(value).ljust(widths[idx]) for idx, value in enumerate(row)))
