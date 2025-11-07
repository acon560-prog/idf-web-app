import React, { useState, useEffect } from "react";
import { buildApiUrl } from "../utils/apiConfig";

const StationSelector = ({ onSelectStation }) => {
  const [stations, setStations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

    useEffect(() => {
    const fetchStations = async () => {
      try {
        const response = await fetch(buildApiUrl("/stations"));
        if (!response.ok) {
          throw new Error("Failed to fetch stations");
        }
        const data = await response.json();

        // Inspect the data to confirm the property names
        console.log("Fetched stations data:", data);

            setStations(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
        };
        fetchStations();
    }, []);

    const handleChange = (event) => {
    const selectedStationId = event.target.value;
    const selectedStation = stations.find(
      (s) => String(s.stationId) === selectedStationId,
    );
    if (selectedStation) {
      // Use logical OR to handle different property names
      const stationName = selectedStation.stationName || selectedStation.name;
      onSelectStation(selectedStation.stationId, stationName);
    }
  };

    if (loading) {
    return <p>Loading stations...</p>;
  }

     if (error) {
    return <p className="text-red-500">Error: {error}</p>;
  }

  if (!Array.isArray(stations) || stations.length === 0) {
    return <p>No stations available.</p>;
  }

    return (
    <div className="mt-4">
      <label
        htmlFor="station-select"
        className="block text-sm font-medium text-gray-700"
      >
        Or select a specific station:
      </label>
      <select
        id="station-select"
        onChange={handleChange}
        className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
      >
        <option value="">-- Select a Station --</option>
        {stations.map((station) => (
          // Use logical OR to handle different property names
          <option key={station.stationId} value={station.stationId}>
            {station.stationName || station.name} (
            {station.province || station.provinceCode})
          </option>
        ))}
      </select>
    </div>
  );
};

export default StationSelector;