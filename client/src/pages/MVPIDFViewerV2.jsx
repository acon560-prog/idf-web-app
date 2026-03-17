import React, {
  useState,
  useEffect,
  useRef,
  useCallback,
  useMemo,
} from "react";
import Autocomplete from "react-google-autocomplete";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { useAuth } from "../context/AuthContext"; // Add this to access user state
import { Link } from "react-router-dom";
import {
  buildApiUrl,
  getApiBaseUrl,
  readJsonResponse,
} from "../utils/apiConfig";
import { useTranslation } from "react-i18next";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
// To make the app functional, please replace 'YOUR_API_KEY' with your actual Google Maps API key.
// Example: const GOOGLE_MAPS_API_KEY = 'AIzaSyB-C1...';
const GOOGLE_MAPS_API_KEY = process.env.REACT_APP_GOOGLE_PLACES_API_KEY || "";
const HAS_GOOGLE_API_KEY = Boolean(
  GOOGLE_MAPS_API_KEY && GOOGLE_MAPS_API_KEY.trim(),
);

const API_BASE_URL = getApiBaseUrl();

const DownloadIcon = (props) => (
  <svg
    {...props}
    xmlns="http://www.w3.org/2000/svg"
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className="lucide lucide-download"
  >
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="7 10 12 15 17 10" />
    <line x1="12" x2="12" y1="15" y2="3" />
  </svg>
);

const CloseIcon = (props) => (
   <svg
    {...props}
    xmlns="http://www.w3.org/2000/svg"
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className="lucide lucude-x"
  >
    <path d="M18 6 6 18" />
    <path d="m6 6 12 12" />
  </svg>
);

const MapPinIcon = (props) => (
  <svg
    {...props}
    xmlns="http://www.w3.org/2000/svg"
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className="lucide lucide-map-pin"
  >
    <path d="M12 18s-2.5-3.5-2.5-5.5a2.5 2.5 0 0 1 5 0c0 2-2.5 5.5-2.5 5.5z" />
    <circle cx="12" cy="12" r="2.5" />
    <path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z" />
  </svg>
);

const SearchIcon = (props) => (
  <svg
    {...props}
    xmlns="http://www.w3.org/2000/svg"
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    className="lucide lucide-search"
  >
    <circle cx="11" cy="11" r="8" />
    <path d="m21 21-4.3-4.3" />
  </svg>
);

const allReturnPeriods = ["2", "5", "10", "25", "50", "100"];

const MVPIDFViewerV2 = () => {
  const auth = useAuth();
  const user = auth?.user ?? null;
  const authFetch = auth?.authFetch ?? null;
  const { t } = useTranslation();
  const [trialMessage, setTrialMessage] = useState("");
  const [station, setStation] = useState(null);
  const [idfData, setIDFData] = useState([]);
  const [applyClimate2050High, setApplyClimate2050High] = useState(false);
  const [applyQc18, setApplyQc18] = useState(false);
  const [climateInfo, setClimateInfo] = useState(null);
  const [allowSubhourFallback, setAllowSubhourFallback] = useState(false);
  const [idfFallbackInfo, setIdfFallbackInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [exportOpen, setExportOpen] = useState(false);
  const [isStationInfoVisible, setIsStationInfoVisible] = useState(false);
  const [showChart, setShowChart] = useState(false);
  const [selectedReturnPeriods, setSelectedReturnPeriods] =
    useState(allReturnPeriods);
  const [place, setPlace] = useState(null);
  const chartDataRef = useRef(null);
  
  const hasGoogleApiKey = HAS_GOOGLE_API_KEY;

  // Cloud Run bugfix: the location input sometimes becomes disabled, which stops typing.
  // Force-keep it enabled.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const el = document.getElementById("location");
    if (!el) return;

    const forceEnable = () => {
      try {
        if (el.disabled) el.disabled = false;
        if (el.hasAttribute("disabled")) el.removeAttribute("disabled");
      } catch (_e) {
        // no-op
      }
    };

    forceEnable();
    const obs = new MutationObserver(() => forceEnable());
    obs.observe(el, { attributes: true, attributeFilter: ["disabled"] });
    return () => obs.disconnect();
  }, []);
  
  const trialExpired = useMemo(() => {
    const message = (trialMessage || "").toLowerCase();
    const errorMessage = (error || "").toLowerCase();
    return (
      message.includes("free trial has expired") ||
      errorMessage.includes("free trial has expired")
    );
  }, [trialMessage, error]);
  
  // We rely on `react-google-autocomplete` to load/init Places correctly.
  useEffect(() => {
    if (!hasGoogleApiKey) {
      setError(
        "Google Maps API key is missing or invalid. Set REACT_APP_GOOGLE_PLACES_API_KEY in your environment or .env file.",
      );
    }
  }, [hasGoogleApiKey]);

  useEffect(() => {
  if (!user) {
    setTrialMessage("");
    return;
  }

  const role = (user.role || "").toLowerCase();
  const hasPaidSubscription = Boolean(user.stripeCustomerId || user.plan);

  // Admins never see trial-expired banner
  if (role === "admin") {
    setTrialMessage("");
    return;
  }

  // Paid non-admin users do not see trial banner
  if (user.subscriptionStatus === "active" && hasPaidSubscription) {
    setTrialMessage("");
    return;
  }

  if (user.trialEndsAt) {
    const endsAt = new Date(user.trialEndsAt);
    const now = new Date();
    const diffMs = endsAt - now;
    if (diffMs > 0) {
      const daysLeft = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
      setTrialMessage(
        `Your free trial ends in ${daysLeft} day${daysLeft !== 1 ? "s" : ""}.`,
      );
    } else {
      setTrialMessage(
        "Your free trial has expired. Please upgrade to continue accessing IDF curves.",
      );
    }
  } else if (user.subscriptionStatus === "trialing") {
    setTrialMessage("Your free trial is active.");
  } else if (user.subscriptionStatus !== "active") {
    setTrialMessage("Your subscription status could not be verified.");
  } else {
    setTrialMessage("");
  }
}, [user]);

  const handleSearch = useCallback(
    async (e) => {
      e.preventDefault();
        setError(null);
        setIDFData([]);
        setClimateInfo(null);
        setIdfFallbackInfo(null);
        setStation(null);
        setShowChart(false);
        setIsStationInfoVisible(false);
        setLoading(true);

      if (!place || !place.geometry) {
        setError("Please select a valid location from the dropdown.");
        setLoading(false);
        return;
      }

      const lat = place.geometry.location.lat();
      const lon = place.geometry.location.lng();
      let provinceCode = "";

      if (place.address_components) {
        for (const component of place.address_components) {
          if (component.types.includes("administrative_area_level_1")) {
            provinceCode = component.short_name;
            break;
          }
        }
      }

    try {
        const params = new URLSearchParams({
          lat: String(lat),
          lon: String(lon),
          province: provinceCode,
        });
        const nearestResponse = await fetch(
          `${buildApiUrl("/nearest-station")}?${params.toString()}`,
        );
        const nearestData = await readJsonResponse(
          nearestResponse,
          "Failed to find nearest station.",
        );
        if (!nearestResponse.ok) {
          throw new Error(
            nearestData?.error || "Failed to find nearest station.",
          );
        }
        const nearestStation = nearestData;
        setStation(nearestStation);
        setIsStationInfoVisible(true);
        console.log("Found nearest station:", nearestStation);

       const idfUrlBase = `${buildApiUrl("/idf/curves")}?stationId=${nearestStation.stationId}`;
       const climateParam = applyClimate2050High
         ? "cc_2050_high"
         : applyQc18
           ? "qc18"
           : "";
       const extraParams = [];
       if (climateParam) extraParams.push(`climate=${encodeURIComponent(climateParam)}`);
       if (allowSubhourFallback) extraParams.push("allowSubhourFallback=1");
       const idfUrl = extraParams.length ? `${idfUrlBase}&${extraParams.join("&")}` : idfUrlBase;

       const idfResponse = await (authFetch
        ? authFetch(
            idfUrl,
          )
        : fetch(
            idfUrl,
          ));

        const idfJson = await readJsonResponse(
          idfResponse,
          "Failed to fetch IDF data.",
        );
        if (!idfResponse.ok) {
          if (
            (idfResponse.status === 402 || idfResponse.status === 403) &&
            idfJson?.code === "trial_expired"
          ) {
            setTrialMessage(
              "Your free trial has expired. Please upgrade to continue accessing IDF curves.",
            );
          }
          throw new Error(idfJson?.error || "Failed to fetch IDF data.");
        }
        setClimateInfo(idfJson?.climate || null);
        setIdfFallbackInfo(idfJson?.fallback || null);
        console.log("Raw IDF data from API:", idfJson.data);

        const processedData = idfJson.data
            .map((item, index) => {
              console.log(`Processing item ${index}:`, item);
              let durationInMinutes = 0;

              // First, check if the duration is a number.
              if (typeof item.duration === "number") {
                console.log(`- Duration is a number: ${item.duration}`);
                durationInMinutes = item.duration;
              } else {
                // If not a number, fall back to the string parsing logic.
                const durationString = String(item.duration);
                console.log(
                  `- Duration is a string: "${durationString}". Attempting to parse.`,
                );
                if (durationString.includes("min")) {
                  durationInMinutes = parseInt(
                    durationString.replace(" min", ""),
                    10,
                  );
                } else if (durationString.includes("h")) {
                  durationInMinutes =
                    parseInt(durationString.replace(" h", ""), 10) * 60;
                } else if (durationString.includes("d")) {
                  durationInMinutes =
                    parseInt(durationString.replace(" d", ""), 10) * 24 * 60;
                }
              }

              console.log(`- Converted to minutes: ${durationInMinutes}`);

          // Skip data points with non-positive duration, as they will break the log scale
              if (durationInMinutes <= 0) {
                console.log(
                  `- Skipping item ${index} due to non-positive duration.`,
                );
                return null;
              }

          const newItem = { duration: durationInMinutes };
              let hasValidData = false;

              allReturnPeriods.forEach((period) => {
                const value = parseFloat(item[period]);
                if (!isNaN(value)) {
                  const durationHours = durationInMinutes / 60;
                  const intensity =
                    durationHours > 0 ? value / durationHours : null;
                  if (
                    intensity !== null &&
                    !isNaN(intensity) &&
                    isFinite(intensity)
                  ) {
                    newItem[period] = intensity;
                    hasValidData = true;
                  }
                } else {
                  console.log(
                    `- Item ${index}: Value for return period "${period}" is not a number.`,
                  );
                }
              });

              if (!hasValidData) {
                console.log(
                  `- Skipping item ${index} because no valid numerical IDF values were found.`,
                );
                return null;
              }

          console.log(`- Successfully processed item ${index}:`, newItem);
              return newItem;
            })
            .filter(Boolean); // Filter out any null items

      const sortedData = processedData.sort(
          (a, b) => a.duration - b.duration,
        );

        console.log("Final processed and sorted data for chart:", sortedData);

          if (sortedData.length > 0) {
            setIDFData(sortedData);
            chartDataRef.current = sortedData;
            setShowChart(true);
          } else {
            setError(
              "No valid IDF curve data could be found for this station. The data may be missing or malformed.",
            );
            setShowChart(false);
          }
        } catch (err) {
          console.error(err);
          const apiHint = API_BASE_URL ? ` (API base: ${API_BASE_URL})` : "";
          setError(
            err.message
              ? `${err.message}${apiHint}`
              : `Unexpected error while contacting the server.${apiHint}`,
          );
        } finally {
          setLoading(false);
        }
      },
      [authFetch, place, applyClimate2050High, applyQc18, allowSubhourFallback],
    );

  const handleCheckboxChange = useCallback((event) => {
    const { value, checked } = event.target;
    setSelectedReturnPeriods((prev) => {
      let newPeriods;
      if (checked) {
        if (!prev.includes(value)) {
          newPeriods = [...prev, value];
        } else {
          newPeriods = prev;
        }
      } else {
        newPeriods = prev.filter((p) => p !== value);
      }
      // Sort the array numerically to ensure the legend order is correct
      return newPeriods.sort((a, b) => parseInt(a) - parseInt(b));
    });
  }, []);

  const handleDownload = useCallback(() => {
    if (chartDataRef.current) {
      const dataStr = JSON.stringify(chartDataRef.current, null, 2);
      const dataUri =
        "data:application/json;charset=utf-8," + encodeURIComponent(dataStr);
      const link = document.createElement("a");
      link.setAttribute("href", dataUri);
      link.setAttribute("download", `idf_data_${station.stationId}.json`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  }, [station]);
  const handleCSVDownload = useCallback(() => {
   if (!chartDataRef.current) return;

   const headers = ["Duration", ...allReturnPeriods.map((p) => `${p}-Year`)];
    const rows = chartDataRef.current.map((item) => {
      return [
        formatDurationLabel(item.duration),
        ...allReturnPeriods.map((p) => item[p] ?? ""),
      ].join(",");
    });

   const csvContent = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);

   const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `idf_data_${station.stationId}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [station]);
  const handleGeoJSONDownload = useCallback(() => {
    if (!chartDataRef.current || !station) return;

    const features = chartDataRef.current.map((row) => ({
      type: "Feature",
      geometry: {
        type: "Point",
        coordinates: [station.lon, station.lat],
      },
      properties: {
        stationId: station.stationId,
        stationName: station.stationName || station.name,
        duration: row.duration,
        ...allReturnPeriods.reduce((acc, period) => {
          acc[`${period}-Year`] = row[period] ?? null;
          return acc;
        }, {}),
      },
    }));

    const geojson = {
      type: "FeatureCollection",
      features,
    };

    const blob = new Blob([JSON.stringify(geojson, null, 2)], {
      type: "application/geo+json",
    });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = `idf_data_${station.stationId}.geojson`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [station]);
  const handlePdfDownload = useCallback(() => {
  if (!idfData?.length || !station) return;

  const doc = new jsPDF();
  doc.setFontSize(14);
  doc.text("IDF Report", 14, 16);

  doc.setFontSize(10);
  doc.text(`Station ID: ${station.stationId}`, 14, 24);
  doc.text(`Station: ${station.stationName || station.name || ""}`, 14, 30);
  doc.text(`Generated: ${new Date().toLocaleString()}`, 14, 36);

  const headers = ["Duration", ...allReturnPeriods.map((p) => `${p}-Year`)];
  const rows = idfData.map((row) => [
    formatDurationLabel(row.duration),
    ...allReturnPeriods.map((p) =>
      row[p] != null && Number.isFinite(row[p]) ? Number(row[p]).toFixed(1) : "-"
    ),
  ]);

  autoTable(doc, {
    startY: 42,
    head: [headers],
    body: rows,
    styles: { fontSize: 9 },
    headStyles: { fillColor: [31, 41, 55] },
  });

  doc.save(`idf_report_${station.stationId}.pdf`);
}, [idfData, station]);
  const getLineColor = (period) => {
    const colors = {
       2: "#03a9f4",
      5: "#4caf50",
      10: "#ffc107",
      25: "#ff5722",
      50: "#9c27b0",
      100: "#e91e63",
    };
    return colors[period] || "#000000";
  };

  const getLineDash = (period) => {
    if (period === "2" || period === "5") {
      return null;
    }
    return "5 5";
  };

  const formatDurationLabel = (minutes) => {
    if (minutes < 60) {
      return `${minutes} min`;
    } else if (minutes === 1440) {
      return `24 hr`;
    } else if (minutes < 1440) {
      const hours = minutes / 60;
      return `${hours} h`;
    } else {
      const days = minutes / 1440;
      return `${days} d`;
    }
  };

  const formatTooltipLabel = (value) => {
    return `Duration: ${formatDurationLabel(value)}`;
  };
  
  const yAxisDomain = useMemo(() => {
    if (!idfData || idfData.length === 0) {
       return [1, "auto"];
    }
    let maxIntensity = 0;
     idfData.forEach((item) => {
      allReturnPeriods.forEach((period) => {
        if (
          item[period] &&
          !isNaN(item[period]) &&
          item[period] > maxIntensity
        ) {
          maxIntensity = item[period];
        }
      });
    });
    const upperLimit = Math.max(Math.ceil(maxIntensity / 10) * 10, 1);
    return [1, upperLimit];
  }, [idfData]);

  if (!user) {
    return (
      <div className="max-w-3xl mx-auto p-6 mt-10 border border-yellow-400 bg-yellow-100 rounded text-center text-yellow-900">
        <p className="mb-4 text-lg font-semibold">
          Please{" "}
          <Link to="/login" className="text-blue-700 underline">
            log in
          </Link>{" "}
          to access IDF curves and tables.
        </p>
      </div>
    );
  }
 
  // No explicit "Loading Maps" gate; Autocomplete component handles script loading.

  return (
    <div className="bg-gray-50 min-h-screen flex flex-col items-center justify-center p-4 sm:p-6 lg:p-8 font-sans">
        {(trialMessage || trialExpired) && (
          <div className="w-full max-w-5xl mb-4">
            <div className="bg-blue-50 border border-blue-200 text-blue-800 px-4 py-3 rounded-lg shadow-sm text-sm space-y-3">
            <p>
              {trialExpired
                ? "Your free trial has expired. Please upgrade to continue accessing IDF curves."
                : trialMessage}
            </p>
              {trialExpired && (
                <div className="flex flex-wrap gap-3">
                  <Link
                    to="/contact"
                    className="inline-flex items-center justify-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition"
                  >
                    Contact us to upgrade
                  </Link>
                  <a
                    href="mailto:support@civispec.com"
                    className="inline-flex items-center justify-center rounded-md border border-indigo-600 px-4 py-2 text-sm font-medium text-indigo-600 hover:bg-indigo-50 transition"
                  >
                    Email support
                  </a>
                </div>
              )}
            </div>
          </div>
        )}
      <div className="w-full max-w-5xl bg-white p-6 sm:p-8 lg:p-10 rounded-2xl shadow-xl flex flex-col md:flex-row gap-6">
        {/* Left Side: Search and Controls */}
        <div className="w-full md:w-1/3 space-y-6">
          <div className="flex justify-between items-center mb-4">
            <h1 className="text-2xl font-bold text-gray-800">IDF Viewer</h1>
            <MapPinIcon className="text-gray-600 text-3xl" />
          </div>

          <p className="text-gray-600">
             Enter a location to find the nearest weather station and its
            Intensity-Duration-Frequency (IDF) curves.
          </p>

          <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm text-gray-700">
            <label className="flex items-start gap-2">
              <input
                type="checkbox"
                checked={applyClimate2050High}
                onChange={(e) => {
                  const next = e.target.checked;
                  setApplyClimate2050High(next);
                  if (next) setApplyQc18(false);
                }}
                className="mt-1"
              />
              <span>
                Apply climate change (Canada, except Québec): <span className="font-semibold">2050 + high emissions (SSP5-8.5)</span>
              </span>
            </label>
            <p className="mt-2 text-xs text-gray-500">
              Uses IDF_CC factors when available for the selected station, otherwise the nearest station with factors.
            </p>
            {applyClimate2050High && (
              <div className="mt-2 text-xs">
                {climateInfo?.applied ? (
                  <div className="text-emerald-700">
                    Climate applied: <span className="font-semibold">Yes</span>
                    {climateInfo?.modelsUsed ? ` (models: ${climateInfo.modelsUsed})` : ""}
                  </div>
                ) : (
                  <div className="text-amber-700">
                    Climate applied: <span className="font-semibold">No</span>
                    {climateInfo?.reason ? ` — ${climateInfo.reason}` : ""}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm text-gray-700">
            <label className="flex items-start gap-2">
              <input
                type="checkbox"
                checked={applyQc18}
                onChange={(e) => {
                  const next = e.target.checked;
                  setApplyQc18(next);
                  if (next) setApplyClimate2050High(false);
                }}
                className="mt-1"
              />
              <span>
                Apply climate change (Québec): <span className="font-semibold">+18% uplift</span>
              </span>
            </label>
            <p className="mt-2 text-xs text-gray-500">
              Applied only to stations in QC.
            </p>
            {applyQc18 && (
              <div className="mt-2 text-xs">
                {climateInfo?.applied ? (
                  <div className="text-emerald-700">
                    Climate applied: <span className="font-semibold">Yes</span> (factor: 1.18)
                  </div>
                ) : (
                  <div className="text-amber-700">
                    Climate applied: <span className="font-semibold">No</span>
                    {climateInfo?.reason ? ` — ${climateInfo.reason}` : ""}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm text-gray-700">
            <label className="flex items-start gap-2">
              <input
                type="checkbox"
                checked={allowSubhourFallback}
                onChange={(e) => setAllowSubhourFallback(e.target.checked)}
                className="mt-1"
              />
              <span>
                If the selected station has no <span className="font-semibold">5–30 min</span> data, use the nearest station for short durations
              </span>
            </label>
            <p className="mt-2 text-xs text-gray-500">
              Some ECCC stations have missing sub-hour data; enabling this keeps your table/plot on the standard short-duration grid.
            </p>
            {idfFallbackInfo?.shortDurationFallback && (
              <div className="mt-2 text-xs text-amber-700">
                Using short-duration IDF from{" "}
                <span className="font-semibold">
                  {idfFallbackInfo.shortDurationUsedStationName || "nearest station"}{" "}
                </span>
                {idfFallbackInfo.shortDurationUsedStationId
                  ? `(${idfFallbackInfo.shortDurationUsedStationId})`
                  : ""}
                {typeof idfFallbackInfo.shortDurationDistanceKm === "number"
                  ? ` — ${idfFallbackInfo.shortDurationDistanceKm} km`
                  : ""}
                .
              </div>
            )}
          </div>

          <form onSubmit={handleSearch} className="space-y-4">
             <div>
                <label
                  htmlFor="location"
                  className="block text-sm font-medium text-gray-700"
                >
                  Location
                </label>
                <Autocomplete
                  apiKey={GOOGLE_MAPS_API_KEY}
                  onPlaceSelected={(selectedPlace) => {
                    if (!selectedPlace || !selectedPlace.geometry) return;
                    setPlace(selectedPlace);
                  }}
                  options={{
                    types: ["(cities)"],
                    componentRestrictions: { country: "ca" },
                  }}
                  id="location"
                  name="location"
                  placeholder="e.g., Montreal, QC"
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
                />
              </div>
            <button
              type="submit"
              className="w-full inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={loading || !HAS_GOOGLE_API_KEY}
            >
              {loading ? (
                <div className="flex items-center">
                  <svg
                    className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  <span>Searching...</span>
                </div>
              ) : (
                <>
                  <SearchIcon className="mr-2 h-5 w-5" />
                  <span>Find Station</span>
                </>
              )}
            </button>
          </form>

          {error && (
            <div
              className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg relative"
              role="alert"
            >
              <span className="block sm:inline">{error}</span>
            </div>
          )}

          {isStationInfoVisible && station && (
            <div className="bg-gray-100 p-4 rounded-md mt-4 shadow">
              <div className="flex justify-between items-center mb-2">
                <h3 className="font-semibold text-gray-700">Station Found</h3>
                <button onClick={() => setIsStationInfoVisible(false)}>
                  <CloseIcon className="h-4 w-4 text-gray-500 hover:text-gray-700" />
                </button>
              </div>
              <p className="text-gray-600">
                 <strong className="text-gray-800">ID:</strong>{" "}
                {station.stationId}
              </p>
              <p className="text-gray-600">
                 <strong className="text-gray-800">Name:</strong>{" "}
                {station.stationName || station.name || ""}
              </p>
              <p className="text-gray-600">
                 <strong className="text-gray-800">Latitude:</strong>{" "}
                {station.lat}
              </p>
              <p className="text-gray-600">
                <strong className="text-gray-800">Longitude:</strong>{" "}
                {station.lon}
              </p>
                <p className="text-gray-600">
                <strong className="text-gray-800">Distance:</strong>{" "}
                {station.distance_km} km
              </p>
            </div>
          )}
        </div>

        {/* Right Side: Chart and Checkbox Controls. Hidden until a search is successful. */}
        {showChart && (
          <div className="w-full md:w-2/3 space-y-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-800">IDF Curves</h2>
              <div className="relative">
                <button
                  type="button"
                  disabled={!idfData.length}
                  title={!idfData.length ? t("idf.export.emptyHint") : ""}
                  onClick={() => setExportOpen((v) => !v)}
                  className="inline-flex items-center justify-center rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <DownloadIcon className="mr-2 h-4 w-4" />
                  {t("idf.export.button")}
                  <span className="ml-2 text-xs">▾</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    handlePdfDownload();
                    setExportOpen(false);
                  }}
                  className="w-full px-3 py-2 text-left hover:bg-gray-50"
                >
                  <div className="text-sm font-semibold">{t("idf.export.items.pdf.label")}</div>
                  <div className="text-[11px] text-gray-500">{t("idf.export.items.pdf.hint")}</div>
                </button>  
                {exportOpen && !!idfData.length && (
                  <div className="absolute right-0 z-30 mt-2 w-64 max-w-[90vw] overflow-hidden rounded-md border border-gray-200 bg-white shadow-lg">
                    <button
                      type="button"
                      onClick={() => {
                        handleCSVDownload();
                        setExportOpen(false);
                      }}
                      className="w-full px-3 py-2 text-left hover:bg-gray-50"
                    >
                      <div className="text-sm font-semibold">{t("idf.export.items.csv.label")}</div>
                      <div className="text-[11px] text-gray-500">{t("idf.export.items.csv.hint")}</div>
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        handleGeoJSONDownload();
                        setExportOpen(false);
                      }}
                      className="w-full px-3 py-2 text-left hover:bg-gray-50"
                    >
                      <div className="text-sm font-semibold">{t("idf.export.items.geojson.label")}</div>
                      <div className="text-[11px] text-gray-500">{t("idf.export.items.geojson.hint")}</div>
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        handleDownload();
                        setExportOpen(false);
                      }}
                      className="w-full px-3 py-2 text-left hover:bg-gray-50"
                    >
                      <div className="text-sm font-semibold">{t("idf.export.items.json.label")}</div>
                      <div className="text-[11px] text-gray-500">{t("idf.export.items.json.hint")}</div>
                    </button>
                  </div>
                )}
              </div>
            </div>

            <div className="flex flex-wrap gap-4 mb-4">
              {allReturnPeriods.map((period) => (
                <label key={period} className="inline-flex items-center">
                  <input
                    type="checkbox"
                    value={period}
                    checked={selectedReturnPeriods.includes(period)}
                    onChange={handleCheckboxChange}
                    className="rounded-md text-indigo-600 focus:ring-indigo-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">
                    {period} Year
                  </span>
                </label>
              ))}
            </div>

            <div className="bg-gray-50 p-4 rounded-lg shadow-inner">
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={idfData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="duration"
                    label={{
                      value: "Duration (min)",
                      position: "insideBottom",
                      offset: -5,
                    }}
                    tick={{ fontSize: 12 }}
                    scale="log"
                    ticks={[1, 2, 5, 10, 15, 30, 60, 120, 360, 720, 1440]}
                    tickFormatter={formatDurationLabel}
                    domain={["dataMin", "dataMax"]}
                  />
                  <YAxis
                    label={{
                      value: "Intensity (mm/h)",
                      angle: -90,
                      position: "insideLeft",
                      offset: 15,
                    }}
                    tick={{ fontSize: 12 }}
                    scale="log"
                    domain={yAxisDomain}
                  />
                  <Tooltip labelFormatter={formatTooltipLabel} />
                  <Legend verticalAlign="bottom" height={36} />
                  {allReturnPeriods.map(
                    (period) =>
                      selectedReturnPeriods.includes(period) && (
                        <Line
                          key={period}
                          type="monotone"
                          dataKey={period}
                          stroke={getLineColor(period)}
                          strokeWidth={2}
                          dot={false}
                          strokeDasharray={getLineDash(period)}
                          isAnimationActive={false}
                          name={`${period}-Year`}
                        />
                      ),
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="bg-white rounded-lg shadow-md overflow-x-auto mt-6">
              <table className="min-w-full text-sm text-left text-gray-700 border">
                <thead className="bg-gray-100 text-xs uppercase text-gray-600">
                  <tr>
                    <th className="px-4 py-2 border">Duration</th>
                    {allReturnPeriods.map((period) => (
                      <th key={period} className="px-4 py-2 border">
                        {period}-Year
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {idfData.map((row, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                       <td className="px-4 py-2 border">
                        {formatDurationLabel(row.duration)}
                      </td>
                      {allReturnPeriods.map((period) => (
                        <td key={period} className="px-4 py-2 border">
                          {row[period] != null ? row[period].toFixed(1) : "-"}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MVPIDFViewerV2;

