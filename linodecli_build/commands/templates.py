"""Implementation of `linode-cli build templates` commands."""

from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path
from typing import Sequence, Dict, Any

import yaml

from ..core import templates as template_core
from . import scaffold as scaffold_cmd


def register(subparsers: argparse._SubParsersAction, _config) -> None:
    parser = subparsers.add_parser("templates", help="List and inspect AI templates")
    parser.set_defaults(func=lambda args: parser.print_help())
    templates_subparsers = parser.add_subparsers(dest="templates_cmd")

    list_parser = templates_subparsers.add_parser("list", help="List available templates")
    list_parser.set_defaults(func=_cmd_list)

    show_parser = templates_subparsers.add_parser("show", help="Show template details")
    show_parser.add_argument("name", help="Template name")
    show_parser.set_defaults(func=_cmd_show)

    # Add scaffold subcommand
    scaffold_cmd.register(templates_subparsers, _config)

    # Add validate subcommand
    validate_parser = templates_subparsers.add_parser("validate", help="Validate a template")
    validate_parser.add_argument("path", help="Path to template directory or template.yml")
    validate_parser.set_defaults(func=_cmd_validate)

    # Add install command
    install_parser = templates_subparsers.add_parser(
        "install",
        help="Install a local template for reuse"
    )
    install_parser.add_argument(
        "path",
        help="Path to template directory (containing template.yml)"
    )
    install_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite if template already exists"
    )
    install_parser.set_defaults(func=_cmd_install)
    
    # Add uninstall command
    uninstall_parser = templates_subparsers.add_parser(
        "uninstall",
        help="Remove an installed user template"
    )
    uninstall_parser.add_argument(
        "name",
        help="Template name to uninstall"
    )
    uninstall_parser.set_defaults(func=_cmd_uninstall)


def _cmd_list(args):
    """List all bundled and user templates."""
    records = template_core.list_template_records()
    
    if not records:
        print("No templates found.")
        return
    
    rows = []
    for record in records:
        try:
            template = template_core.load_template(record.name)
            desc = template.description.strip().replace("\n", " ")
            if len(desc) > 50:  # Shorten to make room for source column
                desc = desc[:47] + "..."
            
            # Show source: bundled or user
            source = "user" if record.source == "user" else "bundled"
            
            rows.append((
                template.name,
                template.version,
                source,
                desc
            ))
        except Exception:
            continue
    
    if rows:
        _print_table(("NAME", "VERSION", "SOURCE", "DESCRIPTION"), rows)


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


def _cmd_validate(args) -> None:
    """Validate a template for correctness."""
    path = Path(args.path)
    
    # Determine template file path
    if path.is_dir():
        template_file = path / "template.yml"
    elif path.is_file() and path.name in ["template.yml", "template-stub.yml"]:
        template_file = path
    else:
        print(f"Error: '{path}' is not a template directory or .yml file", file=sys.stderr)
        sys.exit(1)
    
    if not template_file.exists():
        print(f"Error: Template file not found: {template_file}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Validating template: {template_file}\n")
    
    # Load and parse YAML
    try:
        with open(template_file, 'r') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"✗ YAML parsing error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error reading file: {e}", file=sys.stderr)
        sys.exit(1)
    
    if not isinstance(data, dict):
        print("✗ Template must be a YAML object/dictionary", file=sys.stderr)
        sys.exit(1)
    
    # Validation checks
    errors = []
    warnings = []
    
    # Required fields
    required_fields = {
        "name": str,
        "display_name": str,
        "version": str,
        "description": str,
        "deploy": dict,
    }
    
    for field, expected_type in required_fields.items():
        if field not in data:
            errors.append(f"Missing required field: {field}")
        elif not isinstance(data[field], expected_type):
            errors.append(f"Field '{field}' must be {expected_type.__name__}")
    
    # Validate deploy section
    if "deploy" in data and isinstance(data["deploy"], dict):
        deploy = data["deploy"]
        
        if deploy.get("target") != "linode":
            errors.append("deploy.target must be 'linode'")
        
        if "linode" not in deploy:
            errors.append("Missing deploy.linode section")
        else:
            linode = deploy["linode"]
            
            # Required Linode fields
            for field in ["image", "region_default", "type_default"]:
                if field not in linode:
                    errors.append(f"Missing deploy.linode.{field}")
            
            # Validate container section for Docker runtime
            capabilities = data.get("capabilities", {})
            runtime = capabilities.get("runtime", "docker")
            
            if runtime == "docker":
                if "container" not in linode:
                    errors.append("Missing deploy.linode.container section for Docker runtime")
                else:
                    container = linode["container"]
                    
                    # Required container fields
                    for field in ["image", "internal_port", "external_port"]:
                        if field not in container:
                            errors.append(f"Missing deploy.linode.container.{field}")
                    
                    # Recommend health check
                    if "health" not in container:
                        warnings.append("No health check defined (recommended)")
                    else:
                        health = container["health"]
                        if health.get("type") == "http" and "path" not in health:
                            errors.append("HTTP health check missing 'path' field")
                        if "port" not in health:
                            warnings.append("Health check missing 'port' field")
    
    # Validate capabilities
    if "capabilities" in data:
        cap = data["capabilities"]
        
        if "runtime" in cap:
            valid_runtimes = ["docker", "native", "k3s"]
            if cap["runtime"] not in valid_runtimes:
                errors.append(f"Invalid runtime: {cap['runtime']} (must be one of {valid_runtimes})")
        
        if "features" in cap:
            if not isinstance(cap["features"], list):
                errors.append("capabilities.features must be a list")
        
        if "packages" in cap:
            if not isinstance(cap["packages"], list):
                errors.append("capabilities.packages must be a list")
    
    # Validate env section
    if "env" in data:
        env = data["env"]
        
        for section in ["required", "optional"]:
            if section in env:
                if not isinstance(env[section], list):
                    errors.append(f"env.{section} must be a list")
                else:
                    for idx, item in enumerate(env[section]):
                        if not isinstance(item, dict):
                            errors.append(f"env.{section}[{idx}] must be an object")
                        elif "name" not in item:
                            errors.append(f"env.{section}[{idx}] missing 'name' field")
    
    # Version format
    if "version" in data:
        version = str(data["version"])
        parts = version.split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            warnings.append(f"Version '{version}' should follow semantic versioning (X.Y.Z)")
    
    # GPU recommendations
    if "deploy" in data and isinstance(data["deploy"], dict):
        linode = data["deploy"].get("linode", {})
        container = linode.get("container", {})
        capabilities_cfg = data.get("capabilities", {})
        
        # Check for legacy requires_gpu
        if container.get("requires_gpu"):
            warnings.append(
                "Using deprecated 'requires_gpu: true'. "
                "Consider using capabilities.features: [gpu-nvidia]"
            )
        
        # Check GPU instance type
        instance_type = linode.get("type_default", "")
        has_gpu_cap = "gpu-nvidia" in capabilities_cfg.get("features", [])
        has_gpu_legacy = container.get("requires_gpu", False)
        
        if (has_gpu_cap or has_gpu_legacy) and not instance_type.startswith("g6-"):
            warnings.append(
                f"GPU capability enabled but instance type '{instance_type}' "
                "doesn't appear to be a GPU instance (should start with 'g6-')"
            )
        
        # Check base image for GPU
        base_image = linode.get("image", "")
        if (has_gpu_cap or has_gpu_legacy) and "ubuntu22.04" not in base_image.lower():
            warnings.append(
                f"GPU instances work best with ubuntu22.04, but using '{base_image}'"
            )
    
    # Print results
    if errors:
        print("Validation FAILED:\n")
        for error in errors:
            print(f"  ✗ {error}")
        print()
    else:
        print("✓ All required fields present")
        print("✓ Schema validation passed")
        print()
    
    if warnings:
        print("Warnings:\n")
        for warning in warnings:
            print(f"  ⚠ {warning}")
        print()
    
    if errors:
        sys.exit(1)
    else:
        if not warnings:
            print("✓ Template validation successful!")
        else:
            print("✓ Template is valid (with warnings)")


def _cmd_install(args) -> None:
    """Install a local template to user templates directory."""
    from ..core import user_templates
    
    path = Path(args.path).resolve()
    
    # Validate path
    if not path.is_dir():
        print(f"Error: '{path}' is not a directory", file=sys.stderr)
        sys.exit(1)
    
    template_file = path / "template.yml"
    if not template_file.exists():
        print(f"Error: No template.yml found in {path}", file=sys.stderr)
        sys.exit(1)
    
    # Load template to get name and validate
    try:
        with open(template_file, 'r') as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"Error: Invalid template.yml: {e}", file=sys.stderr)
        sys.exit(1)
    
    if not isinstance(data, dict):
        print("Error: template.yml must contain a YAML object", file=sys.stderr)
        sys.exit(1)
    
    template_name = data.get("name")
    if not template_name:
        print("Error: template.yml must contain a 'name' field", file=sys.stderr)
        sys.exit(1)
    
    template_version = data.get("version", "unknown")
    
    # Check if already installed
    if not args.force and user_templates.get_user_template_path(template_name):
        print(f"Error: Template '{template_name}' is already installed", file=sys.stderr)
        print(f"Use --force to overwrite", file=sys.stderr)
        sys.exit(1)
    
    # Install
    try:
        if args.force and user_templates.get_user_template_path(template_name):
            user_templates.remove_user_template(template_name)
        
        installed_path = user_templates.add_user_template(template_name, path)
        
        print(f"✓ Installed template '{template_name}' v{template_version}")
        print(f"  Location: {installed_path}")
        print()
        print("You can now use it with:")
        print(f"  linode-cli build init {template_name}")
    
    except Exception as e:
        print(f"Error installing template: {e}", file=sys.stderr)
        sys.exit(1)


def _cmd_uninstall(args) -> None:
    """Uninstall a user template."""
    from ..core import user_templates
    
    template_name = args.name
    
    # Check if it's a user template
    if not user_templates.get_user_template_path(template_name):
        print(f"Error: Template '{template_name}' is not installed", file=sys.stderr)
        print()
        print("List installed templates with:")
        print("  linode-cli build templates list")
        sys.exit(1)
    
    # Remove it
    try:
        user_templates.remove_user_template(template_name)
        print(f"✓ Uninstalled template '{template_name}'")
    except Exception as e:
        print(f"Error uninstalling template: {e}", file=sys.stderr)
        sys.exit(1)
