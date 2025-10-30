// File: MVP_IDFViewer.js
import React, { useState, useEffect } from 'react';
import ProjectWizard from './ProjectWizard';
import IdfChart from '../components/IdfChart';

export default function MVP_IDFViewer() {
  const [stations, setStations] = useState(null);
  const [selectedStation, setSelectedStation] = useState(null);
  const [idfData, setIdfData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stationsLoaded, setStationsLoaded] = useState(false);

  useEffect(() => {
    console.log('Fetching stations...');
    fetch('/api/stations')
      .then(res => {
        if (!res.ok) throw new Error(`Failed to load stations: ${res.status}`);
        return res.json();
      })
      .then(data => {
        console.log('Stations loaded:', data.length);
        setStations(data);
        setStationsLoaded(true);
      })
      .catch(err => {
        console.error('Failed to load stations:', err);
        setError(err.message);
        setStations([]);
        setStationsLoaded(true);
      });
  }, []);

  useEffect(() => {
  // This console.log will show you the value of selectedStation whenever it changes
    console.log('MVP_IDFViewer useEffect triggered with selectedStation:', selectedStation);
     // This check is what prevents the fetch call if no station is selected
    if (!selectedStation || !selectedStation.stationId) {
      // Clear data when no station is selected or it's invalid
      setIdfData(null);
      return;
    }
    
    console.log('Fetching IDF data for station:', selectedStation.id);
    
    // **This is the key fix:** Resetting idfData and error before a new fetch
    setIdfData(null);
    setError(null);
    setLoading(true);

    fetch(`/api/idf/curves?stationId=${selectedStation.stationId}`)
      .then(res => {
        // If the response is a 404, we'll handle it here
        if (res.status === 404) {
          throw new Error('IDF data not found for this station.');
        }
        if (!res.ok) {
          throw new Error(`Failed to load IDF data: ${res.status}`);
        }
        return res.json();
      })
       .then(data => {
        // This console.log will show you the data received from the backend
        console.log('IDF data loaded. Received data structure:', data); // Add this line
        setIdfData(data.data);
      })
      .catch(err => {
        console.error('Failed to load IDF data:', err);
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, [selectedStation]);// This hook is triggered every time selectedStation changes

  const handleStationSelect = (station) => {
    // This console.log will show you the station object coming from ProjectWizard
    console.log('MVP_IDFViewer received station selection:', station);
    setSelectedStation(station);
  };

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h1 className="text-4xl font-bold mb-8 text-center">Select Project Location</h1>
      
      {/* Conditionally render based on the loading state */}
      {!stationsLoaded && <div className="text-center">Loading stations...</div>}
      {stationsLoaded && stations && (
        <ProjectWizard stations={stations} onStationSelect={handleStationSelect} />
      )}
      {/* Handle error for stations fetch */}
      {stationsLoaded && !stations && <div className="text-center text-red-600">Failed to load stations.</div>}
      
      {loading && <p className="text-center text-blue-600 font-medium">Loading IDF data...</p>}
      {error && <p className="text-center text-red-600 font-medium mb-4">{error}</p>}
      
      {idfData && selectedStation && (
        <>
          <h2 className="text-2xl font-semibold mb-4 text-center">
            IDF Curves for {selectedStation.name}
          </h2>
          <div className="p-4 border rounded shadow-md bg-white">
            <IdfChart idfData={idfData} />
          </div>
        </>
      )}
    </div>
  );
}