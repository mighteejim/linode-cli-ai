"""User templates management.

User templates are stored at ~/.config/linode-cli.d/build/templates/
and persist across plugin upgrades.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from .templates import TemplateRecord, TemplateError


def user_templates_dir() -> Path:
    """Return path to user templates directory."""
    config_dir = Path.home() / ".config" / "linode-cli.d" / "build" / "templates"
    return config_dir


def user_templates_index_path() -> Path:
    """Return path to user templates index file."""
    return user_templates_dir() / "index.yml"


def load_user_templates_index() -> List["TemplateRecord"]:
    """Load user templates from index file.
    
    Returns:
        List of TemplateRecord for user-installed templates
    """
    from .templates import TemplateRecord
    
    index_path = user_templates_index_path()
    
    if not index_path.exists():
        return []
    
    try:
        with open(index_path, 'r') as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        # If index is corrupted, return empty list
        return []
    
    records = []
    for entry in data.get("templates", []):
        if "name" not in entry or "path" not in entry:
            continue
        records.append(
            TemplateRecord(
                name=entry["name"],
                path=entry["path"],
                source="user"
            )
        )
    
    return records


def save_user_templates_index(records: List["TemplateRecord"]) -> None:
    """Save user templates index to disk.
    
    Args:
        records: List of TemplateRecord to save
    """
    index_path = user_templates_index_path()
    index_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to dict format for YAML
    data = {
        "templates": [
            {"name": r.name, "path": r.path}
            for r in records
        ]
    }
    
    with open(index_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def add_user_template(name: str, template_dir: Path) -> Path:
    """Copy a template to user templates directory.
    
    Args:
        name: Template name (from template.yml)
        template_dir: Source directory containing template.yml
    
    Returns:
        Path to installed template directory
    
    Raises:
        ValueError: If template already exists
        TemplateError: If template.yml is invalid
    """
    from .templates import TemplateError, TemplateRecord
    
    # Validate source directory
    if not template_dir.is_dir():
        raise TemplateError(f"Source path is not a directory: {template_dir}")
    
    template_file = template_dir / "template.yml"
    if not template_file.exists():
        raise TemplateError(f"No template.yml found in {template_dir}")
    
    # Check if already exists
    if get_user_template_path(name) is not None:
        raise ValueError(f"Template '{name}' is already installed")
    
    # Create destination directory
    dest_dir = user_templates_dir() / name
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    
    # Copy entire template directory
    shutil.copytree(template_dir, dest_dir)
    
    # Update index
    records = load_user_templates_index()
    records.append(
        TemplateRecord(
            name=name,
            path=str(dest_dir / "template.yml"),
            source="user"
        )
    )
    save_user_templates_index(records)
    
    return dest_dir


def remove_user_template(name: str) -> bool:
    """Remove a user template.
    
    Args:
        name: Template name to remove
    
    Returns:
        True if removed, False if not found
    """
    template_path = get_user_template_path(name)
    if template_path is None:
        return False
    
    # Remove directory
    if template_path.exists():
        shutil.rmtree(template_path)
    
    # Update index
    records = load_user_templates_index()
    records = [r for r in records if r.name != name]
    save_user_templates_index(records)
    
    return True


def list_user_template_names() -> List[str]:
    """Return list of installed user template names.
    
    Returns:
        List of template names
    """
    records = load_user_templates_index()
    return [r.name for r in records]


def get_user_template_path(name: str) -> Optional[Path]:
    """Get filesystem path to a user template.
    
    Args:
        name: Template name
    
    Returns:
        Path to template directory, or None if not found
    """
    template_dir = user_templates_dir() / name
    
    # Check if directory exists and has template.yml
    if template_dir.exists() and (template_dir / "template.yml").exists():
        return template_dir
    
    return None
