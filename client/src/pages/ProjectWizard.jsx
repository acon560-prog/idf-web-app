// File: client/src/pages/ProjectWizard.jsx
import React, { useState } from "react";
import LocationSearch from "../components/LocationSearch";

const ProjectWizard = ({ stations, onStationSelect }) => {
  const [selectedStation, setSelectedStation] = useState(null);

  const handleNext = (station) => {
    console.log("Station selected in ProjectWizard:", station); // Debug log
    setSelectedStation(station);
    onStationSelect(station);
  };

  // Add loading check to prevent rendering with undefined stations
  if (!stations) {
    return <div>Loading stations...</div>;
  }

  return (
    <div className="mb-8 flex justify-center">
      <LocationSearch stations={stations} onStationSelected={handleNext} />
      {selectedStation && (
        <p className="mt-4 text-gray-700">
          Selected station:{" "}
          <span className="font-semibold">{selectedStation.name}</span>
          {/* Fix the key names here */}
          (Lat: {selectedStation.lat}, Lon: {selectedStation.lon})
        </p>
      )}
    </div>
  );
};

export default ProjectWizard;
