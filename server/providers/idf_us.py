"""USA IDF provider skeleton with first live NOAA Atlas 14 fetch support."""

from __future__ import annotations

import ast
import copy
import json
import os
import re
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_RETURN_PERIODS: List[str] = ["2", "5", "10", "25", "50", "100"]
DEFAULT_DURATION_MINUTES: List[int] = [5, 10, 15, 30, 60, 120, 360, 720, 1440]
SUPPORTED_SERIES: Tuple[str, ...] = ("ams", "pds")
SUPPORTED_DATA_TYPES: Tuple[str, ...] = ("intensity", "depth")
SUPPORTED_ESTIMATES: Tuple[str, ...] = ("mean", "upper", "lower")
RETURN_PERIODS_BY_SERIES: Dict[str, List[str]] = {
    "ams": ["2", "5", "10", "25", "50", "100", "200", "500", "1000"],
    "pds": ["1", "2", "5", "10", "25", "50", "100", "200", "500", "1000"],
}
RETURN_PERIOD_COLUMN_BY_SERIES: Dict[str, Dict[str, int]] = {
    key: {rp: idx for idx, rp in enumerate(values)}
    for key, values in RETURN_PERIODS_BY_SERIES.items()
}
DEFAULT_SERIES = "ams"
DEFAULT_DATA_TYPE = "intensity"
DEFAULT_ESTIMATE = "mean"

NOAA_DURATION_MINUTES_BY_INDEX: List[int] = [
    5, 10, 15, 30, 60, 120, 180, 360, 720, 1440, 2880, 4320, 5760, 10080, 14400, 28800, 43200, 64800, 86400
]
NOAA_PFDS_CGI_URL = os.environ.get("NOAA_PFDS_CGI_URL", "https://hdsc.nws.noaa.gov/cgi-bin/new/cgi_readH5.py")
NOAA_TIMEOUT_SECONDS = float(os.environ.get("NOAA_PFDS_TIMEOUT_SECONDS", "10"))
REVERSE_GEOCODE_URL = os.environ.get("US_REVERSE_GEOCODE_URL", "https://nominatim.openstreetmap.org/reverse")
FORWARD_GEOCODE_URL = os.environ.get("US_FORWARD_GEOCODE_URL", "https://nominatim.openstreetmap.org/search")
NOAA_UNITS = (os.environ.get("NOAA_PFDS_UNITS") or "english").strip().lower()
US_IDF_CACHE_TTL_SECONDS = float(os.environ.get("US_IDF_CACHE_TTL_SECONDS", "900"))
US_IDF_CACHE_MAX_ENTRIES = int(os.environ.get("US_IDF_CACHE_MAX_ENTRIES", "256"))
_US_IDF_RESPONSE_CACHE: "OrderedDict[str, Tuple[float, Dict[str, Any], int]]" = OrderedDict()


def _provider_units_label(data_type: str = DEFAULT_DATA_TYPE) -> str:
    is_english = NOAA_UNITS == "english"
    if data_type == "depth":
        return "in" if is_english else "mm"
    return "in/h" if is_english else "mm/h"


def _build_cache_key(
    *,
    lat: Optional[float],
    lon: Optional[float],
    station_id: Optional[str],
    location_query: Optional[str],
    return_periods: Sequence[str],
    durations_minutes: Sequence[int],
    data_type: str,
    series: str,
    estimate: str,
) -> str:
    key_payload = {
        "lat": round(lat, 6) if lat is not None else None,
        "lon": round(lon, 6) if lon is not None else None,
        "stationId": station_id or None,
        "locationQuery": (location_query or "").strip().lower() or None,
        "returnPeriods": list(return_periods),
        "durationsMinutes": [int(v) for v in durations_minutes],
        "dataType": data_type,
        "series": series,
        "estimate": estimate,
        "units": NOAA_UNITS,
    }
    return json.dumps(key_payload, sort_keys=True, separators=(",", ":"))


def _cache_get(cache_key: str) -> Optional[Tuple[Dict[str, Any], int]]:
    if not cache_key or US_IDF_CACHE_TTL_SECONDS <= 0:
        return None
    now = time.monotonic()
    entry = _US_IDF_RESPONSE_CACHE.get(cache_key)
    if not entry:
        return None
    cached_at, payload, status_code = entry
    if now - cached_at > US_IDF_CACHE_TTL_SECONDS:
        _US_IDF_RESPONSE_CACHE.pop(cache_key, None)
        return None
    _US_IDF_RESPONSE_CACHE.move_to_end(cache_key)
    cached_payload = copy.deepcopy(payload)
    provider = cached_payload.setdefault("provider", {})
    provider["cache"] = "hit"
    return cached_payload, status_code


def _cache_set(cache_key: str, payload: Dict[str, Any], status_code: int) -> None:
    if not cache_key or US_IDF_CACHE_TTL_SECONDS <= 0 or status_code != 200:
        return
    _US_IDF_RESPONSE_CACHE[cache_key] = (time.monotonic(), copy.deepcopy(payload), status_code)
    _US_IDF_RESPONSE_CACHE.move_to_end(cache_key)
    while len(_US_IDF_RESPONSE_CACHE) > max(1, US_IDF_CACHE_MAX_ENTRIES):
        _US_IDF_RESPONSE_CACHE.popitem(last=False)


def _finalize_response(payload: Dict[str, Any], status_code: int, cache_key: Optional[str]) -> Tuple[Dict[str, Any], int]:
    provider = payload.setdefault("provider", {})
    provider.setdefault("cache", "miss")
    if cache_key:
        _cache_set(cache_key, payload, status_code)
    return payload, status_code


def _coerce_float(value: Any, name: str) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {name}.") from exc


def _parse_return_periods(raw: Any, *, series: str) -> List[str]:
    columns = RETURN_PERIOD_COLUMN_BY_SERIES.get(series, RETURN_PERIOD_COLUMN_BY_SERIES[DEFAULT_SERIES])
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return [value for value in DEFAULT_RETURN_PERIODS if value in columns]
    if isinstance(raw, (list, tuple, set)):
        values = [str(item).strip() for item in raw]
    else:
        values = [part.strip() for part in str(raw).split(",")]
    filtered = [value for value in values if value in columns]
    return filtered or [value for value in DEFAULT_RETURN_PERIODS if value in columns]


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


def _parse_series(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    if value in SUPPORTED_SERIES:
        return value
    return DEFAULT_SERIES


def _parse_data_type(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    if value in SUPPORTED_DATA_TYPES:
        return value
    return DEFAULT_DATA_TYPE


def _parse_estimate(raw: Any) -> str:
    value = str(raw or "").strip().lower()
    if value in SUPPORTED_ESTIMATES:
        return value
    return DEFAULT_ESTIMATE


def _build_base_payload(
    *,
    lat: Optional[float],
    lon: Optional[float],
    station_id: Optional[str],
    return_periods: List[str],
    durations_minutes: List[int],
    data_type: str = DEFAULT_DATA_TYPE,
    series: str = DEFAULT_SERIES,
    estimate: str = DEFAULT_ESTIMATE,
    location_query: Optional[str] = None,
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
            "units": _provider_units_label(data_type),
            "dataType": data_type,
            "series": series,
            "estimate": estimate,
            "endpoint": NOAA_PFDS_CGI_URL,
        },
        "request": {
            "lat": lat,
            "lon": lon,
            "stationId": station_id,
            "locationQuery": location_query,
            "returnPeriods": return_periods,
            "durationsMinutes": durations_minutes,
            "dataType": data_type,
            "series": series,
            "estimate": estimate,
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


def _fetch_noaa_pfds_point(lat: float, lon: float, *, data_type: str, series: str) -> Dict[str, Any]:
    query = urlencode(
        {
            "lat": f"{lat:.6f}",
            "lon": f"{lon:.6f}",
            "type": "pf",
            "data": data_type,
            "units": NOAA_UNITS if NOAA_UNITS in {"english", "metric"} else "english",
            "series": series,
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
    upper = _extract_js_assignment(body, "upper")
    lower = _extract_js_assignment(body, "lower")
    if not isinstance(upper, list):
        upper = quantiles
    if not isinstance(lower, list):
        lower = quantiles

    return {
        "quantiles": quantiles,
        "upper": upper,
        "lower": lower,
        "region": _extract_js_assignment(body, "region"),
        "volume": _extract_js_assignment(body, "volume"),
        "version": _extract_js_assignment(body, "version"),
        "source_file": _extract_js_assignment(body, "file"),
        "series": _extract_js_assignment(body, "ser"),
        "data_type": _extract_js_assignment(body, "datatype"),
        "units": _extract_js_assignment(body, "unit"),
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
        "lat": lat,
        "lon": lon,
        "city": city,
        "state": state,
        "countryCode": country_code,
        "displayName": display_name,
        "source": "nominatim",
    }


def _forward_geocode_location_query(query_text: str) -> Optional[Dict[str, Any]]:
    query = urlencode(
        {
            "format": "jsonv2",
            "q": query_text,
            "countrycodes": "us",
            "limit": "1",
            "addressdetails": "1",
        }
    )
    request = Request(
        f"{FORWARD_GEOCODE_URL}?{query}",
        headers={"User-Agent": "civispec-us-idf/1.0"},
    )
    try:
        with urlopen(request, timeout=NOAA_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except Exception:
        return None

    if not isinstance(payload, list) or not payload:
        return None

    first = payload[0]
    if not isinstance(first, dict):
        return None

    lat_value = _to_float(first.get("lat"))
    lon_value = _to_float(first.get("lon"))
    if lat_value is None or lon_value is None:
        return None

    address = first.get("address") or {}
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
    country_code = (address.get("country_code") or "").upper() or "US"
    display_name = first.get("display_name")
    label_parts = [part for part in [city, state] if part]
    label = ", ".join(label_parts) if label_parts else (display_name or query_text)

    return {
        "label": label,
        "lat": lat_value,
        "lon": lon_value,
        "city": city,
        "state": state,
        "countryCode": country_code,
        "displayName": display_name,
        "source": "nominatim_search",
    }


def _to_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_rows_from_noaa_values(
    values_matrix: Sequence[Sequence[Any]],
    *,
    durations_minutes: Sequence[int],
    return_periods: Sequence[str],
    series: str,
) -> List[Dict[str, Any]]:
    requested_durations = set(durations_minutes)
    columns_by_period = RETURN_PERIOD_COLUMN_BY_SERIES.get(series, RETURN_PERIOD_COLUMN_BY_SERIES[DEFAULT_SERIES])
    columns = [(rp, columns_by_period[rp]) for rp in return_periods if rp in columns_by_period]
    rows: List[Dict[str, Any]] = []

    for idx, row in enumerate(values_matrix):
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
    location_query: Any = None,
    return_periods: Any = None,
    durations_minutes: Any = None,
    data_type: Any = None,
    series: Any = None,
    estimate: Any = None,
    **_kwargs: Any,
) -> Tuple[Dict[str, Any], int]:
    selected_series = _parse_series(series)
    selected_data_type = _parse_data_type(data_type)
    selected_estimate = _parse_estimate(estimate)
    rp_values = _parse_return_periods(return_periods, series=selected_series)
    duration_values = _parse_durations(durations_minutes)
    station_id_str = str(station_id).strip() if station_id is not None else None
    location_query_str = str(location_query).strip() if location_query is not None else None
    if location_query_str == "":
        location_query_str = None

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
            data_type=selected_data_type,
            series=selected_series,
            estimate=selected_estimate,
            location_query=location_query_str,
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
            data_type=selected_data_type,
            series=selected_series,
            estimate=selected_estimate,
            location_query=location_query_str,
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
            data_type=selected_data_type,
            series=selected_series,
            estimate=selected_estimate,
            location_query=location_query_str,
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
        data_type=selected_data_type,
        series=selected_series,
        estimate=selected_estimate,
        location_query=location_query_str,
    )
    cache_key = _build_cache_key(
        lat=lat_value,
        lon=lon_value,
        station_id=station_id_str,
        location_query=location_query_str,
        return_periods=rp_values,
        durations_minutes=duration_values,
        data_type=selected_data_type,
        series=selected_series,
        estimate=selected_estimate,
    )
    cached_response = _cache_get(cache_key)
    if cached_response:
        return cached_response
    payload["location"] = {
        "label": f"{lat_value:.4f}, {lon_value:.4f}" if lat_value is not None and lon_value is not None else None,
        "lat": lat_value,
        "lon": lon_value,
        "city": None,
        "state": None,
        "countryCode": "US",
        "source": "input",
    }

    # PR6: first live NOAA fetch path by coordinates.
    if lat_value is None or lon_value is None:
        if location_query_str:
            geocoded = _forward_geocode_location_query(location_query_str)
            if geocoded:
                lat_value = geocoded["lat"]
                lon_value = geocoded["lon"]
                payload["request"]["lat"] = lat_value
                payload["request"]["lon"] = lon_value
                payload["location"] = geocoded
            else:
                payload["provider"]["status"] = "geocode_not_found"
                payload["provider"]["code"] = "us_provider_geocode_not_found"
                payload["provider"]["message"] = "Could not resolve that U.S. location name. Try a city, town, or ZIP."
                payload["code"] = "us_provider_geocode_not_found"
                payload["message"] = payload["provider"]["message"]
                return _finalize_response(payload, 200, cache_key)
        else:
            payload["provider"]["status"] = "awaiting_coordinates"
            payload["provider"]["message"] = "Provide US latitude/longitude or a location name for live NOAA Atlas 14 retrieval."
            payload["message"] = payload["provider"]["message"]
            return _finalize_response(payload, 200, cache_key)

    resolved_location = _reverse_geocode_location(lat_value, lon_value)
    if resolved_location:
        payload["location"] = resolved_location

    try:
        noaa_data = _fetch_noaa_pfds_point(
            lat_value,
            lon_value,
            data_type=selected_data_type,
            series=selected_series,
        )
        values_key = {
            "mean": "quantiles",
            "upper": "upper",
            "lower": "lower",
        }.get(selected_estimate, "quantiles")
        rows = _build_rows_from_noaa_values(
            noaa_data.get(values_key) or noaa_data["quantiles"],
            durations_minutes=duration_values,
            return_periods=rp_values,
            series=selected_series,
        )
        payload["data"] = rows
        payload["provider"]["status"] = "live_preview"
        payload["provider"]["code"] = "us_provider_live_preview"
        payload["provider"]["dataType"] = selected_data_type
        payload["provider"]["series"] = selected_series
        payload["provider"]["estimate"] = selected_estimate
        payload["provider"]["units"] = _provider_units_label(selected_data_type)
        payload["provider"]["message"] = (
            "NOAA Atlas 14 live retrieval succeeded "
            f"({selected_data_type}, {selected_series.upper()}, {selected_estimate})."
        )
        payload["code"] = "us_provider_live_preview"
        payload["message"] = payload["provider"]["message"]
        payload["queryPlan"]["ready"] = True
        payload["source"] = {
            "region": noaa_data.get("region"),
            "volume": noaa_data.get("volume"),
            "version": noaa_data.get("version"),
            "file": noaa_data.get("source_file"),
            "units": noaa_data.get("units"),
            "series": noaa_data.get("series"),
            "dataType": noaa_data.get("data_type"),
        }
        if not rows:
            payload["provider"]["status"] = "live_no_matching_rows"
            payload["provider"]["code"] = "us_provider_no_matching_rows"
            payload["provider"]["message"] = (
                "NOAA response was received, but no rows matched the requested durations/return periods "
                f"for {selected_data_type}, {selected_series.upper()}, {selected_estimate}."
            )
            payload["code"] = "us_provider_no_matching_rows"
            payload["message"] = payload["provider"]["message"]
        return _finalize_response(payload, 200, cache_key)
    except LookupError as exc:
        friendly_message = _normalize_noaa_error_message(str(exc))
        payload["provider"]["status"] = "live_no_coverage"
        payload["provider"]["code"] = "us_provider_no_coverage"
        payload["provider"]["message"] = friendly_message
        payload["code"] = "us_provider_no_coverage"
        payload["message"] = friendly_message
        payload["error"] = str(exc)
        return _finalize_response(payload, 200, cache_key)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        payload["provider"]["status"] = "live_fetch_failed"
        payload["provider"]["code"] = "us_provider_fetch_failed"
        payload["provider"]["message"] = f"NOAA fetch failed: {exc}"
        payload["code"] = "us_provider_fetch_failed"
        payload["message"] = "US provider temporary fallback: NOAA fetch failed."
        payload["error"] = str(exc)
        return _finalize_response(payload, 200, cache_key)
