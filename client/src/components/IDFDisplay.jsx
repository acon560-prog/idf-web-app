import React, { useState } from 'react';

function IDFDisplay() {
  const [stationId, setStationId] = useState('YourStation');
  const [units, setUnits] = useState('mm/hr');
  const [tableData, setTableData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function loadData() {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/idf-table?station_id=${stationId}&units=${units}`);
      if (!response.ok) throw new Error('Failed to load data');
      const data = await response.json();
      setTableData(data);
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  }

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h1 className="text-4xl font-bold mb-8 text-center">IDF Curves and Table</h1>

      <div className="flex flex-wrap gap-4 justify-center mb-8">
        <input
          type="text"
          placeholder="Enter Station ID"
          value={stationId}
          onChange={(e) => setStationId(e.target.value)}
          className="border border-gray-300 rounded p-3 w-48 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        <select
          value={units}
          onChange={(e) => setUnits(e.target.value)}
          className="border border-gray-300 rounded p-3 w-32 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="mm/hr">mm/hr</option>
          <option value="in/hr">in/hr</option>
        </select>

        <button
          onClick={loadData}
          disabled={loading}
          className={`px-6 py-3 rounded text-white font-semibold transition
            ${loading ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'}`}
        >
          {loading ? 'Loading...' : 'Load Data'}
        </button>
      </div>

      {error && (
        <div className="bg-red-100 text-red-700 p-4 rounded mb-6 text-center">{error}</div>
      )}

      {tableData.length > 0 && (
        <>
          <h2 className="text-2xl font-semibold mb-4">IDF Table</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full border border-gray-300 rounded-md text-left">
              <thead className="bg-blue-600 text-white">
                <tr>
                  <th className="px-4 py-2">Duration</th>
                  <th className="px-4 py-2">2 Year</th>
                  <th className="px-4 py-2">5 Year</th>
                  <th className="px-4 py-2">10 Year</th>
                  <th className="px-4 py-2">25 Year</th>
                  <th className="px-4 py-2">50 Year</th>
                  <th className="px-4 py-2">100 Year</th>
                </tr>
              </thead>
              <tbody>
                {tableData.map((row, idx) => (
                  <tr
                    key={idx}
                    className={idx % 2 === 0 ? 'bg-gray-100' : ''}
                  >
                    <td className="border-t border-gray-300 px-4 py-2">{row.duration}</td>
                    <td className="border-t border-gray-300 px-4 py-2">{row['2'].toFixed(2)}</td>
                    <td className="border-t border-gray-300 px-4 py-2">{row['5'].toFixed(2)}</td>
                    <td className="border-t border-gray-300 px-4 py-2">{row['10'].toFixed(2)}</td>
                    <td className="border-t border-gray-300 px-4 py-2">{row['25'].toFixed(2)}</td>
                    <td className="border-t border-gray-300 px-4 py-2">{row['50'].toFixed(2)}</td>
                    <td className="border-t border-gray-300 px-4 py-2">{row['100'].toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h2 className="mt-8 text-2xl font-semibold mb-4">IDF Curve</h2>
          <img
            alt="IDF Curve"
            src={`/idf-plot?station_id=${stationId}&units=${units}&_=${Date.now()}`}
            className="border rounded max-w-full shadow-lg"
          />
        </>
      )}
    </div>
  );
}

export default IDFDisplay;
