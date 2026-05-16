"""USA IDF provider skeleton with first live NOAA Atlas 14 fetch support."""

from __future__ import annotations

import ast
import json
import os
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_RETURN_PERIODS: List[str] = ["2", "5", "10", "25", "50", "100"]
DEFAULT_DURATION_MINUTES: List[int] = [5, 10, 15, 30, 60, 120, 360, 720, 1440]
SUPPORTED_RETURN_PERIODS: List[str] = ["2", "5", "10", "25", "50", "100", "200", "500", "1000"]
AMS_RETURN_PERIOD_COLUMN = {rp: idx for idx, rp in enumerate(SUPPORTED_RETURN_PERIODS)}

NOAA_DURATION_MINUTES_BY_INDEX: List[int] = [
    5, 10, 15, 30, 60, 120, 180, 360, 720, 1440, 2880, 4320, 5760, 10080, 14400, 28800, 43200, 64800, 86400
]
NOAA_PFDS_CGI_URL = os.environ.get("NOAA_PFDS_CGI_URL", "https://hdsc.nws.noaa.gov/cgi-bin/new/cgi_readH5.py")
NOAA_TIMEOUT_SECONDS = float(os.environ.get("NOAA_PFDS_TIMEOUT_SECONDS", "10"))
REVERSE_GEOCODE_URL = os.environ.get("US_REVERSE_GEOCODE_URL", "https://nominatim.openstreetmap.org/reverse")


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
    filtered = [value for value in values if value in AMS_RETURN_PERIOD_COLUMN]
    return filtered or list(DEFAULT_RETURN_PERIODS)


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


def _build_base_payload(
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
            "endpoint": NOAA_PFDS_CGI_URL,
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


def _extract_js_assignment(body: str, name: str) -> Any:
    match = re.search(rf"\b{name}\s*=\s*(.+?);", body, re.DOTALL)
    if not match:
        return None
    raw = match.group(1).strip()
    try:
        return ast.literal_eval(raw)
    except Exception:
        return None


def _fetch_noaa_pfds_point(lat: float, lon: float) -> Dict[str, Any]:
    query = urlencode(
        {
            "lat": f"{lat:.6f}",
            "lon": f"{lon:.6f}",
            "type": "pf",
            "data": "intensity",
            "units": "metric",
            "series": "ams",
        }
    )
    url = f"{NOAA_PFDS_CGI_URL}?{query}"
    request = Request(url, headers={"User-Agent": "civispec-us-idf/1.0"})
    with urlopen(request, timeout=NOAA_TIMEOUT_SECONDS) as response:
        body = response.read().decode("utf-8", errors="replace")

    result = _extract_js_assignment(body, "result")
    if isinstance(result, str) and result.lower() != "values":
        error_message = (
            _extract_js_assignment(body, "ErrorMsg")
            or _extract_js_assignment(body, "errorMsg")
            or _extract_js_assignment(body, "error")
            or "NOAA PFDS did not return values for this location."
        )
        raise LookupError(str(error_message))

    quantiles = _extract_js_assignment(body, "quantiles")
    if not isinstance(quantiles, list):
        raise ValueError("NOAA response did not include quantiles data.")

    return {
        "quantiles": quantiles,
        "region": _extract_js_assignment(body, "region"),
        "volume": _extract_js_assignment(body, "volume"),
        "version": _extract_js_assignment(body, "version"),
        "source_file": _extract_js_assignment(body, "file"),
    }


def _normalize_noaa_error_message(message: str) -> str:
    text = (message or "").strip()
    if not text:
        return "NOAA PFDS did not return values for this location."
    text = text.replace("\n", " ").strip()
    text = re.sub(r"^Error\s*\d+(\.\d+)?:\s*", "", text, flags=re.IGNORECASE)
    if "not within a project area" in text.lower():
        return (
            "The selected coordinate is outside NOAA PFDS project coverage for this endpoint. "
            "Try a different U.S. coordinate."
        )
    return text


def _reverse_geocode_location(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    query = urlencode(
        {
            "format": "jsonv2",
            "lat": f"{lat:.6f}",
            "lon": f"{lon:.6f}",
            "zoom": "10",
            "addressdetails": "1",
        }
    )
    request = Request(
        f"{REVERSE_GEOCODE_URL}?{query}",
        headers={"User-Agent": "civispec-us-idf/1.0"},
    )
    try:
        with urlopen(request, timeout=NOAA_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    address = payload.get("address") or {}
    if not isinstance(address, dict):
        address = {}

    city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("municipality")
        or address.get("county")
    )
    state = address.get("state")
    country_code = (address.get("country_code") or "").upper() or None
    display_name = payload.get("display_name")

    label_parts = [part for part in [city, state] if part]
    label = ", ".join(label_parts) if label_parts else (display_name or f"{lat:.4f}, {lon:.4f}")

    return {
        "label": label,
        "city": city,
        "state": state,
        "countryCode": country_code,
        "displayName": display_name,
        "source": "nominatim",
    }


def _to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_rows_from_quantiles(
    quantiles: Sequence[Sequence[Any]],
    *,
    durations_minutes: Sequence[int],
    return_periods: Sequence[str],
) -> List[Dict[str, Any]]:
    requested_durations = set(durations_minutes)
    columns = [(rp, AMS_RETURN_PERIOD_COLUMN[rp]) for rp in return_periods if rp in AMS_RETURN_PERIOD_COLUMN]
    rows: List[Dict[str, Any]] = []

    for idx, row in enumerate(quantiles):
        if idx >= len(NOAA_DURATION_MINUTES_BY_INDEX):
            break
        duration = NOAA_DURATION_MINUTES_BY_INDEX[idx]
        if duration not in requested_durations:
            continue
        if not isinstance(row, (list, tuple)):
            continue

        record: Dict[str, Any] = {"duration": duration}
        has_values = False
        for rp, column_idx in columns:
            if column_idx >= len(row):
                continue
            number = _to_float(row[column_idx])
            if number is None:
                continue
            record[rp] = number
            has_values = True

        if has_values:
            rows.append(record)

    rows.sort(key=lambda item: item.get("duration", 0))
    return rows


def get_us_idf_curves(
    *,
    lat: Any = None,
    lon: Any = None,
    station_id: Any = None,
    return_periods: Any = None,
    durations_minutes: Any = None,
    **_kwargs: Any,
) -> Tuple[Dict[str, Any], int]:
    rp_values = _parse_return_periods(return_periods)
    duration_values = _parse_durations(durations_minutes)
    station_id_str = str(station_id).strip() if station_id is not None else None

    try:
        lat_value = _coerce_float(lat, "latitude")
        lon_value = _coerce_float(lon, "longitude")
    except ValueError as exc:
        payload = _build_base_payload(
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
        payload = _build_base_payload(
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
        payload = _build_base_payload(
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

    payload = _build_base_payload(
        lat=lat_value,
        lon=lon_value,
        station_id=station_id_str,
        return_periods=rp_values,
        durations_minutes=duration_values,
    )
    payload["location"] = {
        "label": f"{lat_value:.4f}, {lon_value:.4f}" if lat_value is not None and lon_value is not None else None,
        "city": None,
        "state": None,
        "countryCode": "US",
        "source": "input",
    }

    # PR6: first live NOAA fetch path by coordinates.
    if lat_value is None or lon_value is None:
        payload["provider"]["status"] = "awaiting_coordinates"
        payload["provider"]["message"] = "Provide US latitude/longitude for live NOAA Atlas 14 retrieval."
        payload["message"] = payload["provider"]["message"]
        return payload, 200

    resolved_location = _reverse_geocode_location(lat_value, lon_value)
    if resolved_location:
        payload["location"] = resolved_location

    try:
        noaa_data = _fetch_noaa_pfds_point(lat_value, lon_value)
        rows = _build_rows_from_quantiles(
            noaa_data["quantiles"],
            durations_minutes=duration_values,
            return_periods=rp_values,
        )
        payload["data"] = rows
        payload["provider"]["status"] = "live_preview"
        payload["provider"]["code"] = "us_provider_live_preview"
        payload["provider"]["message"] = "NOAA Atlas 14 live retrieval succeeded."
        payload["code"] = "us_provider_live_preview"
        payload["message"] = "NOAA Atlas 14 live retrieval succeeded."
        payload["queryPlan"]["ready"] = True
        payload["source"] = {
            "region": noaa_data.get("region"),
            "volume": noaa_data.get("volume"),
            "version": noaa_data.get("version"),
            "file": noaa_data.get("source_file"),
        }
        if not rows:
            payload["provider"]["status"] = "live_no_matching_rows"
            payload["provider"]["code"] = "us_provider_no_matching_rows"
            payload["provider"]["message"] = (
                "NOAA response was received, but no rows matched the requested durations/return periods."
            )
            payload["code"] = "us_provider_no_matching_rows"
            payload["message"] = payload["provider"]["message"]
        return payload, 200
    except LookupError as exc:
        friendly_message = _normalize_noaa_error_message(str(exc))
        payload["provider"]["status"] = "live_no_coverage"
        payload["provider"]["code"] = "us_provider_no_coverage"
        payload["provider"]["message"] = friendly_message
        payload["code"] = "us_provider_no_coverage"
        payload["message"] = friendly_message
        payload["error"] = str(exc)
        return payload, 200
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        payload["provider"]["status"] = "live_fetch_failed"
        payload["provider"]["code"] = "us_provider_fetch_failed"
        payload["provider"]["message"] = f"NOAA fetch failed: {exc}"
        payload["code"] = "us_provider_fetch_failed"
        payload["message"] = "US provider temporary fallback: NOAA fetch failed."
        payload["error"] = str(exc)
        return payload, 200
