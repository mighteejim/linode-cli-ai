"""Cloud-init generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

import yaml


@dataclass
class CloudInitConfig:
    container_image: str
    internal_port: int
    external_port: int
    env_vars: Dict[str, str] = field(default_factory=dict)
    post_start_script: Optional[str] = None


def generate_cloud_init(config: CloudInitConfig) -> str:
    """Render a cloud-init YAML payload for provisioning the Linode."""
    write_files = [
        {
            "path": "/etc/build-ai.env",
            "permissions": "0600",
            "owner": "root:root",
            "content": _render_env_file(config.env_vars),
        },
        {
            "path": "/usr/local/bin/start-container.sh",
            "permissions": "0755",
            "owner": "root:root",
            "content": _render_start_script(config),
        },
    ]

    doc = {
        "package_update": True,
        "packages": ["docker.io"],
        "write_files": write_files,
        "runcmd": [["bash", "/usr/local/bin/start-container.sh"]],
    }
    return "#cloud-config\n" + yaml.safe_dump(doc, sort_keys=False)


def _render_env_file(env_vars: Dict[str, str]) -> str:
    """Render dotenv content sorted by key."""
    lines = []
    for key in sorted(env_vars.keys()):
        value = env_vars[key]
        lines.append(f"{key}={value}")
    return "\n".join(lines) + ("\n" if lines else "")


def _render_start_script(config: CloudInitConfig) -> str:
    lines = [
        "#!/bin/bash",
        "set -euo pipefail",
        "CONTAINER_NAME=app",
        "IMAGE=\"%s\"" % config.container_image,
        "EXTERNAL_PORT=%d" % config.external_port,
        "INTERNAL_PORT=%d" % config.internal_port,
        "",
        "systemctl enable docker",
        "systemctl start docker",
        "",
        "docker pull \"$IMAGE\"",
        "docker rm -f \"$CONTAINER_NAME\" >/dev/null 2>&1 || true",
        "docker run -d \\",
        "  --name \"$CONTAINER_NAME\" \\",
        "  --restart unless-stopped \\",
        "  --env-file /etc/build-ai.env \\",
        "  -p ${EXTERNAL_PORT}:${INTERNAL_PORT} \\",
        "  \"$IMAGE\"",
    ]

    if config.post_start_script:
        lines.extend(
            [
                "",
                "# Template post-start hook",
                "cat <<'HOOK' >/usr/local/bin/post-start-hook.sh",
                config.post_start_script.rstrip(),
                "HOOK",
                "chmod +x /usr/local/bin/post-start-hook.sh",
                "bash /usr/local/bin/post-start-hook.sh",
            ]
        )

    lines.append("")
    return "\n".join(lines)
