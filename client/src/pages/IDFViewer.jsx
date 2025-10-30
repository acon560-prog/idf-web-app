import React, { useEffect, useState, useMemo } from "react";
import LocationSearch from '../components/LocationSearch'; // Adjust path to your component
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

export default function IDFViewer() {
  const [stationsMasterList, setStationsMasterList] = useState([]);
  const [selectedStation, setSelectedStation] = useState(null);

  const [mode, setMode] = useState("place");
  const [stationId, setStationId] = useState("7060400");
  const [place, setPlace] = useState("Saguenay, QC");
  const [province, setProvince] = useState("QC");
  const [unitSystem, setUnitSystem] = useState("metric");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  // Fetch stations once on mount
  useEffect(() => {
    fetch('/api/stations')
      .then(res => res.json())
      .then(data => setStationsMasterList(data))
      .catch(err => console.error("Failed to load stations", err));
  }, []);

  // Handler for when LocationSearch selects a station
  const handleStationSelected = (station) => {
    setSelectedStation(station);
    setStationId(station.stationId);
    setPlace(station.name);
    setProvince(station.provinceCode || '');
    setMode('station');
  };

  // Determine the effective stationId to query by
  const effectiveStationId = selectedStation ? selectedStation.stationId : stationId;

  // Build query URL for fetching IDF data
  const query = useMemo(() => {
    const params = new URLSearchParams();
    params.set("unitSystem", unitSystem);
    if (mode === "station") {
      params.set("stationId", effectiveStationId.trim());
    } else {
      params.set("place", place.trim());
      if (province.trim()) params.set("province", province.trim());
    }
    return `/api/idf/curves?${params.toString()}`;
  }, [mode, effectiveStationId, place, province, unitSystem]);

  // Fetch IDF data whenever the query changes
  useEffect(() => {
    async function fetchCurves() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(query);
        if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
        const json = await res.json();
        setData(json);
      } catch (e) {
        setError(e.message);
        setData(null);
      } finally {
        setLoading(false);
      }
    }
    fetchCurves();
  }, [query]);

  // Prepare data for the chart from API response
  const chartData = useMemo(() => {
    if (!data?.durations || !data?.series) return [];
    return data.durations.map((d) => {
      const row = { duration: d };
      for (const s of data.series) {
        const p = s.points.find(pt => pt.x === d);
        row[s.name] = p?.y ?? null;
      }
      return row;
    });
  }, [data]);

  const xTickFmt = (v) => (v >= 60 ? `${v / 60}h` : `${v}m`);

  return (
    <div className="w-full max-w-5xl mx-auto p-4">

      {/* Location search with loaded stations */}
      <LocationSearch
        stations={stationsMasterList}
        onStationSelected={handleStationSelected}
      />

      {/* Existing UI controls */}
      <div className="mb-4 grid grid-cols-1 md:grid-cols-12 gap-3 items-end">

        <div className="md:col-span-2">
          <label className="block text-sm text-gray-600 mb-1">Lookup mode</label>
          <select
            className="w-full border rounded-xl px-3 py-2"
            value={mode}
            onChange={e => setMode(e.target.value)}
          >
            <option value="place">By place</option>
            <option value="station">By stationId</option>
          </select>
        </div>

        {mode === "station" ? (
          <div className="md:col-span-5">
            <label className="block text-sm text-gray-600 mb-1">Station ID</label>
            <input
              className="w-full border rounded-xl px-3 py-2"
              value={stationId}
              onChange={e => {
                setStationId(e.target.value);
                setSelectedStation(null);
              }}
            />
          </div>
        ) : (
          <>
            <div className="md:col-span-5">
              <label className="block text-sm text-gray-600 mb-1">Place</label>
              <input
                className="w-full border rounded-xl px-3 py-2"
                value={place}
                onChange={e => {
                  setPlace(e.target.value);
                  setSelectedStation(null);
                }}
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm text-gray-600 mb-1">Province</label>
              <input
                className="w-full border rounded-xl px-3 py-2"
                value={province}
                onChange={e => {
                  setProvince(e.target.value);
                  setSelectedStation(null);
                }}
              />
            </div>
          </>
        )}

        <div className="md:col-span-3">
          <label className="block text-sm text-gray-600 mb-1">Unit System</label>
          <select
            className="w-full border rounded-xl px-3 py-2"
            value={unitSystem}
            onChange={e => setUnitSystem(e.target.value)}
          >
            <option value="metric">Metric</option>
            <option value="imperial">Imperial</option>
          </select>
        </div>
      </div>

      {/* Loading and error display */}
      {error && <div className="text-red-600 mb-3">{error}</div>}
      {loading && <div>Loading data...</div>}

      {/* Render the IDF curves */}
      {data && (
        <ResponsiveContainer width="100%" height={400}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="duration" tickFormatter={xTickFmt} />
            <YAxis />
            <Tooltip />
            <Legend />
            {data.series.map(serie => (
              <Line
                key={serie.name}
                type="monotone"
                dataKey={serie.name}
                stroke={serie.color || "#8884d8"}
                strokeDasharray={serie.strokeDasharray || "0"}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
