"""Thin Linode API wrapper leveraging linode-cli client."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional


class LinodeAPIError(RuntimeError):
    """Raised when API operations fail."""


class LinodeAPI:
    def __init__(self, config) -> None:
        client = getattr(config, "client", None)
        if client is None:
            raise LinodeAPIError("linode-cli config missing API client")
        self._client = client

    # API endpoints -----------------------------------------------------

    def create_instance(
        self,
        *,
        region: str,
        linode_type: str,
        image: str,
        label: str,
        tags: Optional[list[str]] = None,
        user_data: str,
        group: str = "build-ai",
    ) -> Dict[str, Any]:
        payload = {
            "type": linode_type,
            "region": region,
            "image": image,
            "label": label,
            "tags": tags or [],
            "group": group,
            "user_data": user_data,
        }
        return self._request("post", "linode/instances", payload)

    def get_instance(self, instance_id: int) -> Dict[str, Any]:
        return self._request("get", f"linode/instances/{instance_id}")

    def delete_instance(self, instance_id: int) -> None:
        self._request("delete", f"linode/instances/{instance_id}")

    # Helpers -----------------------------------------------------------

    @staticmethod
    def derive_hostname(ipv4: str) -> str:
        octets = ipv4.split(".")
        return f"{'-'.join(octets)}.ip.linodeusercontent.com"

    def wait_for_status(
        self, instance_id: int, desired: str = "running", timeout: int = 600, poll: int = 10
    ) -> Dict[str, Any]:
        """Poll Linode until it reaches the desired status or timeout."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            data = self.get_instance(instance_id)
            if data.get("status") == desired:
                return data
            time.sleep(poll)
        raise LinodeAPIError(
            f"Linode {instance_id} did not reach status {desired} within {timeout}s"
        )

    def _request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None):
        client_method = getattr(self._client, method, None)
        if client_method is None:
            raise LinodeAPIError(f"linode-cli client missing method {method}")
        if payload is None:
            response = client_method(path)
        else:
            response = client_method(path, payload)
        if isinstance(response, dict) and response.get("errors"):
            raise LinodeAPIError(str(response["errors"]))
        return response
