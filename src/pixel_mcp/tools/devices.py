"""Paired devices (Pixel Watch, autres)."""

from __future__ import annotations

from typing import Any

from ..client import HealthClient


def register(mcp, client: HealthClient) -> None:
    @mcp.tool()
    async def list_paired_devices(
        page_size: int = 50, page_token: str | None = None
    ) -> dict[str, Any]:
        """Lister les appareils appairés à ton compte Google Health (Pixel Watch, etc.)."""
        return await client.get(
            "/users/me/pairedDevices", pageSize=page_size, pageToken=page_token
        )

    @mcp.tool()
    async def get_paired_device(device_id: str) -> dict[str, Any]:
        """Détail d'un appareil appairé (model, dernière sync, batterie si exposé)."""
        return await client.get(f"/users/me/pairedDevices/{device_id}")
