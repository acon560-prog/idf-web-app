import React, { useState, useEffect } from 'react';
import LocationSearch from '../components/LocationSearch'; // Adjust path
import IdfChart from '../components/IdfChart';
import londonCleanIdf from '../mock/london_clean_idf_2b.json';

const API_BASE = 'http://localhost:5000';

const ProjectWizard = () => {
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    location: '',
    projectType: '',
    foundationDepth: '',
    slope: '',
    drainage: '',
    soil: '',
    height: ''
  });
  const [enrichment, setEnrichment] = useState(null);
  const [stations, setStations] = useState([]);
  const [status, setStatus] = useState('');

  // Fetch stations data on mount to pass to LocationSearch
  useEffect(() => {
    fetch('/api/stations')
      .then(res => res.json())
      .then(data => setStations(data))
      .catch(() => setStations([]));
  }, []);

  useEffect(() => {
    if (step === 2 && form.location) {
      const [city = '', province = ''] = form.location.split(',').map(s => s.trim());
      fetch(`${API_BASE}/api/enrich-location`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ city, province })
      })
        .then(res => res.json())
        .then(resData => {
          if (resData.success && resData.data) {
            setEnrichment(resData.data);
          } else {
            setEnrichment(null);
          }
        })
        .catch(() => setEnrichment(null));
    }
  }, [step, form.location]);

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleStationSelected = (station) => {
    setForm({ ...form, location: station.name }); // Update location with selected station name
  };

  const nextStep = () => setStep(prev => Math.min(prev + 1, 3));
  const prevStep = () => setStep(prev => Math.max(prev - 1, 1));

  // ... submit, downloadPDF, checkCompliance etc. remain the same ...

  return (
    <div className="max-w-xl mx-auto p-6 bg-white shadow rounded">
      <h1 style={{ color: 'green', textAlign: 'center' }}>🚧 Project Wizard Loaded! 🚧</h1>
      <h2 className="text-2xl font-bold mb-4">Project Setup ({step}/3)</h2>

      <form>
        {step === 1 && (
          <>
            <LocationSearch
              stations={stations}
              onStationSelected={handleStationSelected}
            />

            <select
              name="projectType"
              value={form.projectType}
              onChange={handleChange}
              className="w-full border p-2"
              required
            >
              <option value="">Select Project Type</option>
              <option value="residential">Residential</option>
              <option value="commercial">Commercial</option>
              <option value="industrial">Industrial</option>
            </select>
          </>
        )}

        {/* Steps 2 & 3 unchanged, keep your inputs and logic here */}

        {/* Navigation buttons */}
        <div className="flex justify-between pt-4">
          {step > 1 && <button type="button" onClick={prevStep} className="px-4 py-2 bg-gray-300">Back</button>}
          {step < 3 && <button type="button" onClick={nextStep} className="ml-auto px-4 py-2 bg-blue-600 text-white">Next</button>}
          {step === 3 && (
            <button type="submit" className="ml-auto px-4 py-2 bg-green-600 text-white" disabled={!enrichment}>Submit</button>
          )}
        </div>
      </form>

      {/* Optional: Show enrichment summary, IDF charts etc. */}
    </div>
  );
};

export default ProjectWizard;
