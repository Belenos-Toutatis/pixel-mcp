"""Convenience wrappers — high-level tools for common queries.

Tous les data types Google Health passent par `users/me/dataTypes/{type}/dataPoints`
+ un filtre AIP-160. Ces wrappers construisent le filtre pour toi.

Trois familles de filtres :
- interval : `{type_snake}.interval.start_time >= "ISO_DATETIME"`
- sample   : `{type_snake}.sample_time.physical_time >= "ISO_DATETIME"`
- date     : `{type_snake}.date >= "YYYY-MM-DD"` (résumés journaliers)
- civil    : `{type_snake}.interval.civil_start_time >= "YYYY-MM-DD"` (exercise)
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from ..client import HealthClient


def _snake(data_type: str) -> str:
    return data_type.replace("-", "_")


def _iso_z(d: datetime) -> str:
    return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _day_range(date_str: str | None, days: int = 1) -> tuple[date, date]:
    if date_str is None:
        d = date.today()
    else:
        d = date.fromisoformat(date_str)
    return d, d + timedelta(days=days)


def _resolve_range(
    base_date: str | None, end_date: str | None, default_days: int = 1
) -> tuple[date, date]:
    """Renvoie (start_date, end_date_exclusive) en dates civiles."""
    if end_date is None:
        return _day_range(base_date, default_days)
    s, _ = _day_range(base_date, 1)
    e, _ = _day_range(end_date, 1)
    return s, e


def _to_iso_z(d: date) -> str:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _interval_filter(data_type: str, start: date, end: date) -> str:
    f = _snake(data_type)
    return (
        f'{f}.interval.start_time >= "{_to_iso_z(start)}" AND '
        f'{f}.interval.start_time < "{_to_iso_z(end)}"'
    )


def _civil_interval_filter(data_type: str, start: date, end: date) -> str:
    f = _snake(data_type)
    return (
        f'{f}.interval.civil_start_time >= "{start.isoformat()}" AND '
        f'{f}.interval.civil_start_time < "{end.isoformat()}"'
    )


def _sample_filter(data_type: str, start: date, end: date) -> str:
    f = _snake(data_type)
    return (
        f'{f}.sample_time.physical_time >= "{_to_iso_z(start)}" AND '
        f'{f}.sample_time.physical_time < "{_to_iso_z(end)}"'
    )


def _date_filter(data_type: str, start: date, end: date) -> str:
    f = _snake(data_type)
    return f'{f}.date >= "{start.isoformat()}" AND {f}.date < "{end.isoformat()}"'


def register(mcp, client: HealthClient) -> None:
    async def _list(data_type: str, filter_expr: str, page_size: int = 1440) -> dict[str, Any]:
        return await client.get(
            f"/users/me/dataTypes/{data_type}/dataPoints",
            filter=filter_expr,
            pageSize=page_size,
        )

    # ─── Activité ────────────────────────────────────────────────────────────
    @mcp.tool()
    async def get_steps(date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
        """Pas (interval). Date 'YYYY-MM-DD' ou None pour aujourd'hui."""
        s, e = _resolve_range(date, end_date)
        return await _list("steps", _interval_filter("steps", s, e), page_size=10000)

    @mcp.tool()
    async def get_distance(date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
        """Distance (mm dans la réponse)."""
        s, e = _resolve_range(date, end_date)
        return await _list("distance", _interval_filter("distance", s, e), page_size=10000)

    @mcp.tool()
    async def get_active_energy_burned(
        date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """Énergie active brûlée (kcal au-delà du métabolisme de base)."""
        s, e = _resolve_range(date, end_date)
        return await _list(
            "active-energy-burned", _interval_filter("active-energy-burned", s, e)
        )

    @mcp.tool()
    async def get_active_zone_minutes(
        date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """Active Zone Minutes (zones Fat Burn / Cardio / Peak)."""
        s, e = _resolve_range(date, end_date)
        return await _list(
            "active-zone-minutes", _interval_filter("active-zone-minutes", s, e)
        )

    @mcp.tool()
    async def get_exercises(date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
        """Séances d'exercice (sessions Pixel Watch / Strava / Garmin / etc. via Health Connect)."""
        s, e = _resolve_range(date, end_date, default_days=7 if date is None else 1)
        return await _list("exercise", _civil_interval_filter("exercise", s, e))

    @mcp.tool()
    async def get_activity_level(
        date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """Niveau d'activité par tranche (sédentaire / léger / modéré / intense)."""
        s, e = _resolve_range(date, end_date)
        return await _list("activity-level", _interval_filter("activity-level", s, e))

    @mcp.tool()
    async def get_sedentary_period(
        date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """Périodes sédentaires longues."""
        s, e = _resolve_range(date, end_date)
        return await _list("sedentary-period", _interval_filter("sedentary-period", s, e))

    # ─── Cardio ──────────────────────────────────────────────────────────────
    @mcp.tool()
    async def get_heart_rate(
        date: str | None = None, end_date: str | None = None, page_size: int = 10000
    ) -> dict[str, Any]:
        """FC (samples). Une journée = potentiellement plusieurs milliers de points."""
        s, e = _resolve_range(date, end_date)
        return await _list("heart-rate", _sample_filter("heart-rate", s, e), page_size=page_size)

    @mcp.tool()
    async def get_resting_heart_rate(
        date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """FC repos journalière (résumé)."""
        s, e = _resolve_range(date, end_date, default_days=30 if date is None else 1)
        return await _list(
            "daily-resting-heart-rate", _date_filter("daily-resting-heart-rate", s, e)
        )

    @mcp.tool()
    async def get_heart_rate_zones(
        date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """Temps quotidien par zone HR."""
        s, e = _resolve_range(date, end_date)
        return await _list(
            "daily-heart-rate-zones", _date_filter("daily-heart-rate-zones", s, e)
        )

    @mcp.tool()
    async def get_hrv(date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
        """HRV nocturne (RMSSD), résumé quotidien."""
        s, e = _resolve_range(date, end_date, default_days=30 if date is None else 1)
        return await _list(
            "daily-heart-rate-variability",
            _date_filter("daily-heart-rate-variability", s, e),
        )

    @mcp.tool()
    async def get_hrv_intraday(
        date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """HRV par samples (5 min) pendant la nuit."""
        s, e = _resolve_range(date, end_date)
        return await _list(
            "heart-rate-variability",
            _sample_filter("heart-rate-variability", s, e),
            page_size=10000,
        )

    @mcp.tool()
    async def get_vo2_max(date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
        """Estimation VO2max (Cardio Fitness Score) — résumé quotidien."""
        s, e = _resolve_range(date, end_date, default_days=30 if date is None else 1)
        return await _list("daily-vo2-max", _date_filter("daily-vo2-max", s, e))

    @mcp.tool()
    async def get_run_vo2_max(
        date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """VO2max estimé à partir des courses (samples par séance)."""
        s, e = _resolve_range(date, end_date, default_days=30 if date is None else 1)
        return await _list("run-vo2-max", _sample_filter("run-vo2-max", s, e))

    # ─── Sommeil ─────────────────────────────────────────────────────────────
    @mcp.tool()
    async def get_sleep(date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
        """Sessions de sommeil avec phases et score.

        Note: Google Health filtre les sessions de sommeil sur l'heure de FIN
        (l'heure de réveil), pas l'heure de coucher. La date fournie correspond
        donc au jour de réveil.
        """
        s, e = _resolve_range(date, end_date)
        # Sleep uses end_time, not start_time, because sessions cross midnight.
        flt = (
            f'sleep.interval.end_time >= "{_to_iso_z(s)}" AND '
            f'sleep.interval.end_time < "{_to_iso_z(e)}"'
        )
        return await _list("sleep", flt)

    @mcp.tool()
    async def get_sleep_temperature(
        date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """Variation de température cutanée pendant le sommeil (quotidien)."""
        s, e = _resolve_range(date, end_date, default_days=30 if date is None else 1)
        return await _list(
            "daily-sleep-temperature-derivations",
            _date_filter("daily-sleep-temperature-derivations", s, e),
        )

    # ─── Wellness ────────────────────────────────────────────────────────────
    @mcp.tool()
    async def get_spo2(date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
        """SpO2 nocturne — samples."""
        s, e = _resolve_range(date, end_date)
        return await _list(
            "oxygen-saturation", _sample_filter("oxygen-saturation", s, e), page_size=10000
        )

    @mcp.tool()
    async def get_daily_spo2(
        date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """SpO2 — résumé quotidien."""
        s, e = _resolve_range(date, end_date, default_days=30 if date is None else 1)
        return await _list(
            "daily-oxygen-saturation", _date_filter("daily-oxygen-saturation", s, e)
        )

    @mcp.tool()
    async def get_respiratory_rate(
        date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """Fréquence respiratoire nocturne (résumé par sommeil)."""
        s, e = _resolve_range(date, end_date, default_days=30 if date is None else 1)
        return await _list(
            "respiratory-rate-sleep-summary",
            _interval_filter("respiratory-rate-sleep-summary", s, e),
        )

    @mcp.tool()
    async def get_daily_respiratory_rate(
        date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """Fréquence respiratoire quotidienne (moyenne)."""
        s, e = _resolve_range(date, end_date, default_days=30 if date is None else 1)
        return await _list(
            "daily-respiratory-rate", _date_filter("daily-respiratory-rate", s, e)
        )

    @mcp.tool()
    async def get_core_body_temperature(
        date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """Température corporelle (rare — appareils compatibles)."""
        s, e = _resolve_range(date, end_date)
        return await _list(
            "core-body-temperature", _sample_filter("core-body-temperature", s, e)
        )

    # ─── Corps ───────────────────────────────────────────────────────────────
    @mcp.tool()
    async def get_weight(date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
        """Pesées (grammes)."""
        s, e = _resolve_range(date, end_date, default_days=90 if date is None else 1)
        return await _list("weight", _sample_filter("weight", s, e))

    @mcp.tool()
    async def get_body_fat(
        date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """% masse grasse."""
        s, e = _resolve_range(date, end_date, default_days=90 if date is None else 1)
        return await _list("body-fat", _sample_filter("body-fat", s, e))

    @mcp.tool()
    async def get_height(date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
        """Taille (rare update)."""
        s, e = _resolve_range(date, end_date, default_days=365 if date is None else 1)
        return await _list("height", _sample_filter("height", s, e))

    @mcp.tool()
    async def get_blood_glucose(
        date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """Glycémie (capteur compatible)."""
        s, e = _resolve_range(date, end_date)
        return await _list("blood-glucose", _sample_filter("blood-glucose", s, e))

    # ─── Nutrition ───────────────────────────────────────────────────────────
    @mcp.tool()
    async def get_nutrition_log(
        date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """Journal alimentaire (entrées loggées)."""
        s, e = _resolve_range(date, end_date)
        return await _list("nutrition-log", _interval_filter("nutrition-log", s, e))

    @mcp.tool()
    async def get_hydration_log(
        date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """Hydratation (verres d'eau loggés)."""
        s, e = _resolve_range(date, end_date)
        return await _list("hydration-log", _interval_filter("hydration-log", s, e))

    # ─── Cardio événements ───────────────────────────────────────────────────
    @mcp.tool()
    async def get_ecg(date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
        """ECG (Pixel Watch) — classification + waveform."""
        s, e = _resolve_range(date, end_date, default_days=30 if date is None else 1)
        return await _list("electrocardiogram", _interval_filter("electrocardiogram", s, e))

    @mcp.tool()
    async def get_irn_alerts(
        date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """Notifications de rythme cardiaque irrégulier."""
        s, e = _resolve_range(date, end_date, default_days=30 if date is None else 1)
        return await _list(
            "irregular-rhythm-notification",
            _interval_filter("irregular-rhythm-notification", s, e),
        )

    @mcp.tool()
    async def get_swim_lengths(
        date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """Longueurs de natation (par session)."""
        s, e = _resolve_range(date, end_date, default_days=7 if date is None else 1)
        return await _list("swim-lengths-data", _interval_filter("swim-lengths-data", s, e))

    # ─── Agrégat journalier (pour les types qui ne supportent pas list) ─────
    @mcp.tool()
    async def get_floors_daily(
        date: str | None = None, end_date: str | None = None
    ) -> dict[str, Any]:
        """Étages quotidiens — passe par dailyRollUp (floors ne supporte pas list)."""
        s, e = _resolve_range(date, end_date)
        return await client.post(
            "/users/me/dataTypes/floors/dataPoints:dailyRollUp",
            body={
                "startDate": s.isoformat(),
                "endDate": e.isoformat(),
            },
        )
