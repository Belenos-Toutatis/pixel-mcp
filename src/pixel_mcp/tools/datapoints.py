"""Generic dataPoints tools — list, get, create, patch, batch delete, rollups, TCX export.

L'API Google Health v4 expose UNE seule resource générique
`users/me/dataTypes/{type}/dataPoints` qui couvre toutes les données.
"""

from __future__ import annotations

from typing import Any

from ..client import HealthClient, DATA_TYPES


def _check_type(data_type: str) -> None:
    if data_type not in DATA_TYPES:
        # On laisse passer : l'API peut exposer d'autres types non répertoriés.
        pass


def register(mcp, client: HealthClient) -> None:
    @mcp.tool()
    async def list_supported_data_types() -> list[str]:
        """Liste des dataType identifiers connus (kebab-case) — à utiliser avec les autres tools."""
        return DATA_TYPES

    @mcp.tool()
    async def list_data_points(
        data_type: str,
        filter: str | None = None,
        page_size: int = 1440,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """Lister les data points d'un type donné.

        Args:
            data_type: identifier kebab-case (ex: 'steps', 'heart-rate', 'sleep', 'exercise',
                'oxygen-saturation', 'heart-rate-variability', 'weight'…).
                Voir list_supported_data_types().
            filter: expression AIP-160 (ex: 'steps.interval.start_time >= "2026-05-01T00:00:00Z"
                AND steps.interval.start_time < "2026-05-28T00:00:00Z"'). Le préfixe du champ
                correspond au data_type en snake_case (ex: heart_rate, body_fat).
            page_size: défaut 1440, max 10000.
            page_token: pour paginer.
        """
        _check_type(data_type)
        return await client.get(
            f"/users/me/dataTypes/{data_type}/dataPoints",
            filter=filter,
            pageSize=min(page_size, 10000),
            pageToken=page_token,
        )

    @mcp.tool()
    async def get_data_point(data_type: str, data_point_id: str) -> dict[str, Any]:
        """Récupérer un data point précis."""
        return await client.get(f"/users/me/dataTypes/{data_type}/dataPoints/{data_point_id}")

    @mcp.tool()
    async def create_data_point(data_type: str, data_point: dict[str, Any]) -> dict[str, Any]:
        """Créer un data point (logger une mesure manuelle).

        Args:
            data_type: ex 'weight', 'hydration-log', 'nutrition-log'.
            data_point: payload DataPoint complet (voir doc Google Health pour le schéma
                spécifique au data_type).
        """
        return await client.post(
            f"/users/me/dataTypes/{data_type}/dataPoints", body=data_point
        )

    @mcp.tool()
    async def patch_data_point(
        data_type: str, data_point_id: str, data_point: dict[str, Any], update_mask: str
    ) -> dict[str, Any]:
        """Modifier un data point existant.

        Args:
            data_type: identifier.
            data_point_id: id du point.
            data_point: nouveau payload.
            update_mask: champs à mettre à jour, séparés par virgule.
        """
        return await client.patch(
            f"/users/me/dataTypes/{data_type}/dataPoints/{data_point_id}",
            body=data_point,
            updateMask=update_mask,
        )

    @mcp.tool()
    async def batch_delete_data_points(data_type: str, names: list[str]) -> dict[str, Any]:
        """Supprimer plusieurs data points en un appel.

        Args:
            data_type: identifier.
            names: liste de noms complets (ex: 'users/me/dataTypes/steps/dataPoints/abc123').
        """
        return await client.post(
            f"/users/me/dataTypes/{data_type}/dataPoints:batchDelete",
            body={"names": names},
        )

    @mcp.tool()
    async def rollup_data_points(
        data_type: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        """Agrégat sur une fenêtre temporelle (rollUp). Voir doc pour le payload exact.

        Args:
            data_type: identifier.
            body: ex {'startTime': '...', 'endTime': '...', 'bucketByTime': {'durationMillis': '3600000'}}.
        """
        return await client.post(
            f"/users/me/dataTypes/{data_type}/dataPoints:rollUp", body=body
        )

    @mcp.tool()
    async def daily_rollup_data_points(
        data_type: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        """Agrégat quotidien (dailyRollUp). Plus simple que rollUp pour les sommes journalières."""
        return await client.post(
            f"/users/me/dataTypes/{data_type}/dataPoints:dailyRollUp", body=body
        )

    @mcp.tool()
    async def reconcile_data_points(
        data_type: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        """Réconcilier des data points en conflit (upsert)."""
        return await client.post(
            f"/users/me/dataTypes/{data_type}/dataPoints:reconcile", body=body
        )

    @mcp.tool()
    async def export_exercise_tcx(data_point_id: str) -> Any:
        """Exporter une séance 'exercise' au format TCX (XML)."""
        return await client.get(
            f"/users/me/dataTypes/exercise/dataPoints/{data_point_id}:exportExerciseTcx"
        )
