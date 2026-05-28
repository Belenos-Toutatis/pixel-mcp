"""High-level write tools: log weight, body fat, hydration, etc. + delete helpers.

Ces wrappers construisent le payload exact attendu par la Google Health API
(format `sampleTime.physicalTime`, unités en grammes/ml/...).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..client import HealthClient


def _now_z() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_when(when: str | None) -> str:
    """Normalise un timestamp utilisateur en ISO-Z UTC.

    - None ou 'now' -> instant courant
    - 'YYYY-MM-DD' -> 12:00:00 UTC ce jour-là
    - 'YYYY-MM-DDTHH:MM:SS' (local naïf) -> ce moment en UTC
    - ISO complet avec timezone -> converti en UTC
    """
    if when is None or when.lower() == "now":
        return _now_z()
    if len(when) == 10:  # date seule
        when = when + "T12:00:00"
    try:
        dt = datetime.fromisoformat(when.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValueError(f"Format date/heure invalide: {when!r}") from e
    if dt.tzinfo is None:
        dt = dt.astimezone()  # interpret as local
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _extract_short_id(name: str) -> str:
    """De 'users/123/dataTypes/weight/dataPoints/456' renvoie '456'."""
    return name.rsplit("/", 1)[-1]


def register(mcp, client: HealthClient) -> None:
    # ─── Écriture corps ──────────────────────────────────────────────────────
    @mcp.tool()
    async def log_weight(weight_kg: float, when: str | None = None) -> dict[str, Any]:
        """Enregistrer une pesée.

        Args:
            weight_kg: poids en kg (ex: 96.5).
            when: timestamp ISO ('2026-05-28T08:30:00', '2026-05-28', 'now'). None = maintenant.
        """
        payload = {
            "weight": {
                "sampleTime": {"physicalTime": _parse_when(when)},
                "weightGrams": int(round(weight_kg * 1000)),
            }
        }
        return await client.post("/users/me/dataTypes/weight/dataPoints", body=payload)

    @mcp.tool()
    async def log_body_fat(fat_percentage: float, when: str | None = None) -> dict[str, Any]:
        """Enregistrer un % de masse grasse.

        Args:
            fat_percentage: pourcentage (ex: 22.5).
            when: timestamp ISO ou None.
        """
        payload = {
            "bodyFat": {
                "sampleTime": {"physicalTime": _parse_when(when)},
                "percentage": fat_percentage,
            }
        }
        return await client.post("/users/me/dataTypes/body-fat/dataPoints", body=payload)

    @mcp.tool()
    async def log_height(height_cm: float, when: str | None = None) -> dict[str, Any]:
        """Enregistrer la taille (rare update)."""
        payload = {
            "height": {
                "sampleTime": {"physicalTime": _parse_when(when)},
                "heightMillimeters": int(round(height_cm * 10)),
            }
        }
        return await client.post("/users/me/dataTypes/height/dataPoints", body=payload)

    # ─── Écriture nutrition ──────────────────────────────────────────────────
    @mcp.tool()
    async def log_hydration(
        amount_ml: float, when: str | None = None, duration_seconds: int = 0
    ) -> dict[str, Any]:
        """Logger une consommation d'eau (ou autre boisson).

        Args:
            amount_ml: volume en ml (ex: 250).
            when: timestamp ISO ou None = maintenant.
            duration_seconds: 0 pour un événement ponctuel.
        """
        start = _parse_when(when)
        # On crée un intervalle court
        from datetime import timedelta
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = start_dt + timedelta(seconds=max(duration_seconds, 1))
        end = end_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        payload = {
            "hydrationLog": {
                "interval": {"startTime": start, "endTime": end},
                "amountMilliliters": amount_ml,
            }
        }
        return await client.post(
            "/users/me/dataTypes/hydration-log/dataPoints", body=payload
        )

    # ─── Suppression ─────────────────────────────────────────────────────────
    @mcp.tool()
    async def delete_data_point_by_id(data_type: str, data_point_id: str) -> dict[str, Any]:
        """Supprimer un data point précis (utile pour annuler une saisie).

        Args:
            data_type: kebab-case (ex: 'weight', 'body-fat', 'hydration-log').
            data_point_id: l'id seul (la partie après le dernier '/' du 'name') OU le 'name' complet.
        """
        short = _extract_short_id(data_point_id)
        await client.delete(f"/users/me/dataTypes/{data_type}/dataPoints/{short}")
        return {"deleted": short, "data_type": data_type}
