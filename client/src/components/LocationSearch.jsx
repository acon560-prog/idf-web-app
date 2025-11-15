import React from "react";
import Autocomplete from "react-google-autocomplete";

const GOOGLE_MAPS_API_KEY =
  process.env.REACT_APP_GOOGLE_PLACES_API_KEY || "";

const LocationSearch = ({ onStationSelected }) => {
  const handlePlaceSelected = place => {
    if (place.geometry && place.geometry.location) {
      const lat = place.geometry.location.lat();
      const lon = place.geometry.location.lng();

      // Make a call to the new server endpoint
      fetch(`/api/nearest-station?lat=${lat}&lon=${lon}`)
        .then(response => {
          if (!response.ok) {
            throw new Error('Could not find nearest station');
          }
          return response.json();
        })
        .then(nearestStation => {
          if (nearestStation) {
            onStationSelected(nearestStation);
          } else {
            console.warn('No nearest station found from server');
          }
        })
        .catch(error => {
          console.error('Error fetching nearest station:', error);
          // Handle error gracefully in the UI
        });
    }
  };

  return (
    <Autocomplete
      apiKey={GOOGLE_MAPS_API_KEY}
      onPlaceSelected={handlePlaceSelected}
      options={{
        //componentRestrictions: { country: 'ca' },
        fields: ["formatted_address", "geometry.location"],
        types: ["(cities)"],
      }}
      placeholder="Type a location"
      style={{ width: 300, height: 40, padding: 10, marginBottom: 20 }}
    />
  );
};

export default LocationSearch;