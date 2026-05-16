"""USA IDF provider scaffold (NOAA Atlas 14 adapter skeleton).

This module intentionally avoids live NOAA calls for now. It defines:
1) input validation and normalization (lat/lon, durations, return periods)
2) a stable placeholder response contract with provider metadata
3) a query-plan envelope that future NOAA integration will execute
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


DEFAULT_RETURN_PERIODS: List[str] = ["2", "5", "10", "25", "50", "100"]
DEFAULT_DURATION_MINUTES: List[int] = [5, 10, 15, 30, 60, 120, 360, 720, 1440]


def _coerce_float(value: Any, name: str) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {name}.") from exc


def _parse_return_periods(raw: Any) -> List[str]:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return list(DEFAULT_RETURN_PERIODS)
    if isinstance(raw, (list, tuple, set)):
        values = [str(item).strip() for item in raw]
    else:
        values = [part.strip() for part in str(raw).split(",")]
    cleaned = [v for v in values if v]
    return cleaned or list(DEFAULT_RETURN_PERIODS)


def _parse_durations(raw: Any) -> List[int]:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return list(DEFAULT_DURATION_MINUTES)

    if isinstance(raw, (list, tuple, set)):
        values = [str(item).strip() for item in raw]
    else:
        values = [part.strip() for part in str(raw).split(",")]

    durations: List[int] = []
    for value in values:
        if not value:
            continue
        minutes = int(float(value))
        if minutes > 0:
            durations.append(minutes)
    return durations or list(DEFAULT_DURATION_MINUTES)


def _build_placeholder_payload(
    *,
    lat: Optional[float],
    lon: Optional[float],
    station_id: Optional[str],
    return_periods: List[str],
    durations_minutes: List[int],
) -> Dict[str, Any]:
    return {
        "country": "US",
        "code": "us_provider_not_implemented",
        "message": "US provider not implemented yet.",
        "data": [],
        "provider": {
            "name": "noaa_atlas_14",
            "status": "adapter_skeleton",
            "code": "us_provider_not_implemented",
            "message": "NOAA Atlas 14 integration scaffold is wired, but live retrieval is not implemented yet.",
            "dataset": "NOAA Atlas 14 PFDS",
            "units": "mm/h",
        },
        "request": {
            "lat": lat,
            "lon": lon,
            "stationId": station_id,
            "returnPeriods": return_periods,
            "durationsMinutes": durations_minutes,
        },
        "queryPlan": {
            "source": "NOAA Atlas 14 PFDS",
            "step": "fetch-grid-point-and-map-to-idf",
            "ready": False,
        },
    }


def get_us_idf_curves(
    *,
    lat: Any = None,
    lon: Any = None,
    station_id: Any = None,
    return_periods: Any = None,
    durations_minutes: Any = None,
    **_kwargs: Any,
) -> Tuple[Dict[str, Any], int]:
    """Return placeholder US curves contract and normalized query plan.

    Returns:
      (payload, http_status)
    """
    rp_values = _parse_return_periods(return_periods)
    duration_values = _parse_durations(durations_minutes)
    station_id_str = str(station_id).strip() if station_id is not None else None

    try:
        lat_value = _coerce_float(lat, "latitude")
        lon_value = _coerce_float(lon, "longitude")
    except ValueError as exc:
        payload = _build_placeholder_payload(
            lat=None,
            lon=None,
            station_id=station_id_str,
            return_periods=rp_values,
            durations_minutes=duration_values,
        )
        payload["code"] = "invalid_coordinates"
        payload["message"] = str(exc)
        payload["error"] = str(exc)
        payload["provider"]["status"] = "invalid_request"
        payload["provider"]["code"] = "invalid_coordinates"
        payload["provider"]["message"] = str(exc)
        return payload, 400

    if lat_value is not None and not (-90.0 <= lat_value <= 90.0):
        payload = _build_placeholder_payload(
            lat=lat_value,
            lon=lon_value,
            station_id=station_id_str,
            return_periods=rp_values,
            durations_minutes=duration_values,
        )
        payload["code"] = "invalid_coordinates"
        payload["message"] = "Latitude out of range. Expected -90..90."
        payload["error"] = payload["message"]
        payload["provider"]["status"] = "invalid_request"
        payload["provider"]["code"] = "invalid_coordinates"
        payload["provider"]["message"] = payload["message"]
        return payload, 400

    if lon_value is not None and not (-180.0 <= lon_value <= 180.0):
        payload = _build_placeholder_payload(
            lat=lat_value,
            lon=lon_value,
            station_id=station_id_str,
            return_periods=rp_values,
            durations_minutes=duration_values,
        )
        payload["code"] = "invalid_coordinates"
        payload["message"] = "Longitude out of range. Expected -180..180."
        payload["error"] = payload["message"]
        payload["provider"]["status"] = "invalid_request"
        payload["provider"]["code"] = "invalid_coordinates"
        payload["provider"]["message"] = payload["message"]
        return payload, 400

    payload = _build_placeholder_payload(
        lat=lat_value,
        lon=lon_value,
        station_id=station_id_str,
        return_periods=rp_values,
        durations_minutes=duration_values,
    )
    return payload, 200
