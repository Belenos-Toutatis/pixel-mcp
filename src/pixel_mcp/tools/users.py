"""Users — identity, profile, settings, IRN profile."""

from __future__ import annotations

from typing import Any

from ..client import HealthClient


def register(mcp, client: HealthClient) -> None:
    @mcp.tool()
    async def get_identity() -> dict[str, Any]:
        """Identité Google Health de l'utilisateur (id utilisateur, legacyUserId)."""
        return await client.get("/users/me/identity")

    @mcp.tool()
    async def get_profile() -> dict[str, Any]:
        """Profil utilisateur (âge, foulées, etc.)."""
        return await client.get("/users/me/profile")

    @mcp.tool()
    async def get_settings() -> dict[str, Any]:
        """Paramètres utilisateur (unités préférées, langue, fuseau, objectifs)."""
        return await client.get("/users/me/settings")

    @mcp.tool()
    async def update_profile(profile: dict[str, Any], update_mask: str) -> dict[str, Any]:
        """Modifier le profil utilisateur.

        Args:
            profile: payload Profile partiel.
            update_mask: champs à modifier séparés par virgule (ex: 'userConfiguredWalkingStrideLengthMm').
        """
        return await client.patch(
            "/users/me/profile", body=profile, updateMask=update_mask
        )

    @mcp.tool()
    async def update_settings(settings: dict[str, Any], update_mask: str) -> dict[str, Any]:
        """Modifier les paramètres utilisateur.

        Args:
            settings: payload Settings partiel.
            update_mask: champs à modifier (ex: 'distanceUnit,temperatureUnit').
        """
        return await client.patch(
            "/users/me/settings", body=settings, updateMask=update_mask
        )

    @mcp.tool()
    async def get_irn_profile() -> dict[str, Any]:
        """Profil de notifications de rythme cardiaque irrégulier (IRN)."""
        return await client.get("/users/me/irnProfile")
