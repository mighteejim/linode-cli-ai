"""Implementation for `linode-cli build init`."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import yaml

from ..core import templates as template_core
from ..core import colors


def _load_template_from_name_or_path(name_or_path: str, version: str | None = None):
    """Load template from either a name (bundled/remote) or a local path.
    
    Args:
        name_or_path: Template name (e.g., 'llm-api') or local path (e.g., './my-template' or '/abs/path')
        version: Version for named templates (ignored for paths)
    
    Returns:
        Template instance
    """
    # Check if it's a file path
    # Paths: ./ ../ / ~ or just . or ..
    is_path = (
        name_or_path in ('.', '..') or
        name_or_path.startswith(('./', '../', '/', '~')) or
        '/' in name_or_path  # Contains slash = probably a path
    )
    
    if is_path:
        path = Path(name_or_path).expanduser().resolve()
        
        # If it's a directory, look for template.yml or template-stub.yml
        if path.is_dir():
            template_file = path / "template.yml"
            if not template_file.exists():
                # Try template-stub.yml
                template_file = path / "template-stub.yml"
                if not template_file.exists():
                    raise FileNotFoundError(
                        f"No template.yml or template-stub.yml found in {path}"
                    )
        elif path.is_file() and path.suffix in ['.yml', '.yaml']:
            template_file = path
        else:
            raise FileNotFoundError(f"Template path not found: {path}")
        
        # Load the template from file
        try:
            with open(template_file, 'r') as f:
                data = yaml.safe_load(f)
        except Exception as e:
            raise template_core.TemplateError(f"Error loading template from {template_file}: {e}")
        
        if not isinstance(data, dict):
            raise template_core.TemplateError(f"Template file must contain a YAML object: {template_file}")
        
        # Create Template instance
        return template_core.Template(
            name=data.get("name", path.stem),
            display_name=data.get("display_name", data.get("name", path.stem)),
            version=str(data.get("version", "0.0.0")),
            description=data.get("description", "").strip(),
            data=data,
        )
    else:
        # It's a template name, use the standard loader
        return template_core.load_template(name_or_path, version=version)


def register(subparsers: argparse._SubParsersAction, config) -> None:
    parser = subparsers.add_parser("init", help="Initialize a project from a template")
    parser.add_argument("template", help="Template name (e.g., 'chat-agent') or local path (e.g., './my-template')")
    parser.add_argument(
        "--directory",
        "-d",
        help="Project directory (defaults to current working directory)",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip interactive prompts, use template defaults",
    )
    parser.set_defaults(func=lambda args: _cmd_init(args, config))


def _cmd_init(args, config):
    # Parse template name and version (e.g., 'chat-agent@0.2.0')
    template_spec = args.template
    version = None
    if '@' in template_spec:
        template_name, version = template_spec.split('@', 1)
    else:
        template_name = template_spec
    
    # Check if template_name is a local path
    template = _load_template_from_name_or_path(template_name, version)
    target_dir = _resolve_directory(args.directory)

    # Files to create
    deploy_yml_path = target_dir / "deploy.yml"
    env_example_path = target_dir / ".env.example"
    readme_path = target_dir / "README.md"

    _ensure_can_write(deploy_yml_path)
    _ensure_can_write(env_example_path)

    # Interactive selection of region and plan (unless --non-interactive)
    deploy_data = template.data.copy()
    if not args.non_interactive:
        deploy_data = _interactive_configure(config, deploy_data)
    
    # Write deploy.yml (complete deployment config, user can edit)
    deploy_yml_path.write_text(
        yaml.safe_dump(deploy_data, sort_keys=False),
        encoding="utf-8",
    )

    env_lines = _render_env_example(template)
    env_example_path.write_text("\n".join(env_lines) + ("\n" if env_lines else ""), encoding="utf-8")

    if not readme_path.exists():
        readme_content = _render_readme(template)
        readme_path.write_text(readme_content, encoding="utf-8")

    print(f"✓ Initialized {template.display_name} in {target_dir}")
    print()
    print("Files created:")
    print(f"  - deploy.yml        (deployment configuration - customize as needed)")
    print(f"  - .env.example      (environment variables template)")
    print(f"  - README.md         (usage instructions)")
    print()
    print("Next steps:")
    print("  1. Review and customize deploy.yml (region, instance type, etc.)")
    print("  2. Copy .env.example to .env and fill in required values")
    print("  3. Run: linode-cli build deploy")
    
    # Print guidance if available
    guidance = template.data.get("guidance", {})
    if guidance.get("summary"):
        print()
        print(guidance["summary"])


def _resolve_directory(directory: str | None) -> Path:
    if directory:
        target = Path(directory).expanduser()
        if target.exists():
            if any(target.iterdir()):
                raise FileExistsError(f"Directory is not empty: {target}")
        else:
            target.mkdir(parents=True, exist_ok=False)
        return target

    target = Path.cwd()
    deploy_yml = target / "deploy.yml"
    if deploy_yml.exists():
        raise FileExistsError(
            f"{deploy_yml} already exists in the current directory. Use --directory to target another path."
        )
    return target


def _ensure_can_write(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"{path} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)


def _render_env_example(template) -> List[str]:
    env_cfg = template.data.get("env", {})
    lines: List[str] = []
    
    # Add required variables
    required = env_cfg.get("required", [])
    if required:
        lines.append("# Required environment variables")
        for item in required:
            name = item.get("name")
            desc = item.get("description", "")
            if desc:
                # Handle multi-line descriptions - prefix each line with #
                for line in desc.strip().split('\n'):
                    lines.append(f"# {line}")
            lines.append(f"{name}=")
            lines.append("")
    
    # Add optional variables
    optional = env_cfg.get("optional", [])
    if optional:
        if required:
            lines.append("")
        lines.append("# Optional environment variables")
        for item in optional:
            name = item.get("name")
            desc = item.get("description", "")
            if desc:
                # Handle multi-line descriptions - prefix each line with #
                for line in desc.strip().split('\n'):
                    lines.append(f"# {line}")
            lines.append(f"# {name}=")
            lines.append("")
    
    if not lines:
        lines.append("# No environment variables required for this template.")
    
    return lines


def _render_readme(template) -> str:
    description = template.description or template.display_name
    content = [
        f"# {template.display_name}",
        "",
        description,
        "",
        "## Quickstart",
        "",
        "1. Copy `.env.example` to `.env` and fill in any required values.",
        "2. Deploy with `linode-cli build deploy`.",
    ]
    return "\n".join(content) + "\n"


def _interactive_configure(config, deploy_data: dict) -> dict:
    """Interactively select region and instance type."""
    import sys
    
    client = config.client
    linode_cfg = deploy_data.get("deploy", {}).get("linode", {})
    
    # Get template defaults
    default_region = linode_cfg.get("region_default")
    default_type = linode_cfg.get("type_default")
    
    print()
    print(colors.header("=== Interactive Configuration ==="))
    print()
    
    # Fetch and select region
    try:
        print(colors.info("Fetching available regions..."))
        # call_operation returns (status_code, response_dict)
        status, response = client.call_operation('regions', 'list')
        regions = response.get('data', []) if status == 200 else []
        if regions:
            region = _select_region(regions, default_region)
        else:
            print(colors.warning(f"Warning: No regions returned. Using template default."))
            region = default_region
    except Exception as e:
        print(colors.warning(f"Warning: Could not fetch regions ({e}). Using template default."))
        region = default_region
    
    # Fetch and select instance type
    try:
        print()
        print(colors.info("Fetching available instance types..."))
        # call_operation returns (status_code, response_dict)
        status, response = client.call_operation('linodes', 'types')
        types = response.get('data', []) if status == 200 else []
        if types:
            instance_type = _select_instance_type(types, default_type)
        else:
            print(colors.warning(f"Warning: No types returned. Using template default."))
            instance_type = default_type
    except Exception as e:
        print(colors.warning(f"Warning: Could not fetch instance types ({e}). Using template default."))
        instance_type = default_type
    
    # Update deploy_data with selections
    if region:
        deploy_data["deploy"]["linode"]["region_default"] = region
    if instance_type:
        deploy_data["deploy"]["linode"]["type_default"] = instance_type
    
    print()
    print(colors.success(f"✓ Selected region: {region or default_region}"))
    print(colors.success(f"✓ Selected instance type: {instance_type or default_type}"))
    
    return deploy_data


def _select_region(regions, default: str) -> str:
    """Interactive region selection grouped by geography."""
    import sys
    
    # Geographic groupings based on country codes
    geo_groups = {
        'Americas': ['us', 'ca'],
        'South America': ['br', 'cl', 'ar'],
        'Europe': ['gb', 'uk', 'de', 'fr', 'nl', 'se', 'it', 'es', 'pl'],
        'Asia': ['jp', 'sg', 'in', 'id', 'kr', 'ae'],
        'Oceania': ['au', 'nz']
    }
    
    # Group regions by geography
    grouped = {geo: [] for geo in geo_groups}
    other = []
    
    for region in regions:
        region_id = region.get('id', '')
        country_code = region_id.split('-')[0] if '-' in region_id else ''
        
        placed = False
        for geo, codes in geo_groups.items():
            if country_code in codes:
                grouped[geo].append(region)
                placed = True
                break
        
        if not placed:
            other.append(region)
    
    # Build ordered list of all regions
    all_regions = []
    
    print()
    print(colors.header("Available Regions:"))
    print("=" * 70)
    
    # Display each geographic group
    for geo in ['Americas', 'Europe', 'Asia', 'South America', 'Oceania']:
        group_regions = sorted(grouped[geo], key=lambda r: r.get('id', ''))
        if not group_regions:
            continue
            
        print()
        print(colors.bold(f"{geo}:"))
        print("-" * 70)
        
        for region in group_regions:
            region_id = region.get('id', 'unknown')
            label = region.get('label', region_id)
            status = region.get('status', 'unknown')
            status_icon = colors.success("✓") if status == "ok" else colors.error("✗")
            default_marker = colors.default(" (default)") if region_id == default else ""
            idx = len(all_regions) + 1
            all_regions.append(region)
            print(f"{idx:3}. {status_icon} {colors.value(region_id):20} - {label}{default_marker}")
    
    # Display other regions if any
    if other:
        print()
        print("Other:")
        print("-" * 70)
        for region in sorted(other, key=lambda r: r.get('id', '')):
            region_id = region.get('id', 'unknown')
            label = region.get('label', region_id)
            status = region.get('status', 'unknown')
            status_icon = "✓" if status == "ok" else "✗"
            default_marker = " (default)" if region_id == default else ""
            idx = len(all_regions) + 1
            all_regions.append(region)
            print(f"{idx:3}. {status_icon} {region_id:20} - {label}{default_marker}")
    
    print("=" * 70)
    
    # Get user selection
    while True:
        prompt = f"\nSelect region [1-{len(all_regions)}] (Enter for default: {colors.default(default)}): "
        choice = input(prompt).strip()
        
        if not choice:
            return default
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(all_regions):
                return all_regions[idx].get('id')
            else:
                print(f"Invalid choice. Please enter 1-{len(all_regions)}")
        except ValueError:
            print("Invalid input. Please enter a number.")


def _select_instance_type(types, default: str) -> str:
    """Interactive instance type selection grouped by plan type."""
    import sys
    
    # Categorize types by plan type
    categorized = {
        'GPU Linodes': [],
        'Accelerated Linodes': [],
        'Premium Linodes': [],
        'High Memory Linodes': [],
        'Dedicated CPU': [],
        'Shared CPU': []
    }
    
    for t in types:
        type_id = t.get('id', '')
        type_class = t.get('class', '')
        
        if type_class == 'gpu':
            categorized['GPU Linodes'].append(t)
        elif type_class == 'accelerated':
            categorized['Accelerated Linodes'].append(t)
        elif type_class == 'premium' or type_id.startswith('g7-premium'):
            categorized['Premium Linodes'].append(t)
        elif 'highmem' in type_id:
            categorized['High Memory Linodes'].append(t)
        elif 'dedicated' in type_id or type_class == 'dedicated':
            categorized['Dedicated CPU'].append(t)
        elif type_class == 'standard':
            categorized['Shared CPU'].append(t)
    
    # Sort each category by price
    for category in categorized:
        categorized[category].sort(key=lambda t: t.get('price', {}).get('hourly', 0))
    
    print()
    print(colors.header("Available Instance Types:"))
    print("=" * 90)
    
    all_types = []
    
    # Display categories in order
    category_order = [
        'GPU Linodes',
        'Accelerated Linodes', 
        'Premium Linodes',
        'High Memory Linodes',
        'Dedicated CPU',
        'Shared CPU'
    ]
    
    for category in category_order:
        category_types = categorized[category]
        if not category_types:
            continue
            
        print()
        print(colors.bold(f"{category}:"))
        print("-" * 90)
        
        # Limit displayed items for large categories
        display_limit = len(category_types) if category in ['GPU Linodes', 'Accelerated Linodes'] else 15
        
        for t in category_types[:display_limit]:
            type_id = t.get('id', 'unknown')
            default_marker = colors.default(" (default)") if type_id == default else ""
            idx = len(all_types) + 1
            all_types.append(t)
            price = t.get('price', {}).get('hourly', 0)
            memory = t.get('memory', 0)
            vcpus = t.get('vcpus', 0)
            disk = t.get('disk', 0)
            gpus = t.get('gpus', 0)
            
            # Show GPU count for GPU instances
            gpu_info = colors.info(f"  {gpus} GPUs") if gpus > 0 else ""
            
            print(f"{idx:3}. {colors.value(type_id):30} {colors.info(f'${price:7.2f}/hr')}  "
                  f"{memory:6}MB RAM  {vcpus:2} vCPUs  {disk:8}MB{gpu_info}{default_marker}")
        
        if len(category_types) > display_limit:
            print(colors.dim(f"     ... and {len(category_types) - display_limit} more"))
    
    print("=" * 90)
    
    # Get user selection
    while True:
        prompt = f"\nSelect instance type [1-{len(all_types)}] (Enter for default: {colors.default(default)}): "
        choice = input(prompt).strip()
        
        if not choice:
            return default
        
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(all_types):
                return all_types[idx].get('id')
            else:
                print(f"Invalid choice. Please enter 1-{len(all_types)}")
        except ValueError:
            print("Invalid input. Please enter a number.")
