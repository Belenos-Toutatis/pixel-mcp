"""Google Health API client — async httpx wrapper."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .auth import TokenManager

API_BASE = "https://health.googleapis.com/v4"


class HealthError(RuntimeError):
    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"Google Health API {status}: {body}")
        self.status = status
        self.body = body


class HealthClient:
    def __init__(self, token_manager: TokenManager | None = None) -> None:
        self._tokens = token_manager or TokenManager()
        self._client = httpx.AsyncClient(timeout=60)

    async def aclose(self) -> None:
        await self._client.aclose()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._tokens.access_token()}",
            "Accept": "application/json",
        }

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: dict | None = None,
    ) -> Any:
        url = f"{API_BASE}{path}" if path.startswith("/") else path
        for _ in range(3):
            resp = await self._client.request(
                method,
                url,
                params=params,
                json=json_body,
                headers=self._headers(),
            )
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", "10"))
                await asyncio.sleep(retry_after)
                continue
            if resp.status_code >= 400:
                raise HealthError(resp.status_code, resp.text[:1000])
            if resp.status_code == 204 or not resp.content:
                return None
            ctype = resp.headers.get("content-type", "")
            if "application/json" in ctype:
                return resp.json()
            return resp.content
        raise HealthError(429, "Rate-limited after retries.")

    async def get(self, path: str, **params) -> Any:
        return await self.request("GET", path, params={k: v for k, v in params.items() if v is not None})

    async def post(self, path: str, body: dict | None = None) -> Any:
        return await self.request("POST", path, json_body=body)

    async def patch(self, path: str, body: dict | None = None, **params) -> Any:
        return await self.request(
            "PATCH",
            path,
            params={k: v for k, v in params.items() if v is not None},
            json_body=body,
        )


# Catalogue connu des dataTypes (kebab-case) — informatif pour Claude.
DATA_TYPES = [
    "steps", "floors", "distance", "altitude",
    "exercise", "active-zone-minutes", "active-minutes", "activity-level",
    "active-energy-burned", "sedentary-period",
    "heart-rate", "daily-resting-heart-rate", "daily-heart-rate-zones",
    "time-in-heart-rate-zone", "heart-rate-variability",
    "daily-heart-rate-variability",
    "vo2-max", "daily-vo2-max", "run-vo2-max",
    "oxygen-saturation", "daily-oxygen-saturation",
    "respiratory-rate-sleep-summary", "daily-respiratory-rate",
    "core-body-temperature", "daily-sleep-temperature-derivations",
    "blood-glucose", "weight", "body-fat", "height",
    "sleep",
    "nutrition-log", "hydration-log", "food",
    "swim-lengths-data",
    "electrocardiogram", "irregular-rhythm-notification",
]
