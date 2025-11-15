import React, { useState } from 'react';
import Autocomplete from 'react-google-autocomplete';
const GOOGLE_MAPS_API_KEY =
  process.env.REACT_APP_GOOGLE_PLACES_API_KEY || "";
const TestAutocomplete = () => {
  const [selectedPlace, setSelectedPlace] = useState(null);

  return (
    <div>
      <h2>Test Location Autocomplete</h2>
      <Autocomplete
        apiKey={GOOGLE_MAPS_API_KEY}
        onPlaceSelected={(place) => {
          setSelectedPlace(place);
          console.log(place);
        }}
        options={{
          types: ['(cities)'],
          componentRestrictions: { country: 'ca' },
          fields: ['formatted_address', 'geometry.location'],
        }}
        placeholder="Type a location"
        style={{ width: 300, height: 40, padding: 10 }}
      />
      {selectedPlace && <p>You selected: {selectedPlace.formatted_address}</p>}
    </div>
  );
};

export default TestAutocomplete;
