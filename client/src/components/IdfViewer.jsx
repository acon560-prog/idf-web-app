// File: components/IdfViewer.jsx
import React, { useEffect, useState, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import html2canvas from 'html2canvas';

function IdfViewer({ location, idfData }) {
  const [chartData, setChartData] = useState([]);
  const chartRef = useRef(null);

  useEffect(() => {
    if (idfData) {
      const returnPeriods = ['2yr', '5yr', '10yr', '25yr', '50yr', '100yr'];
      const formatted = returnPeriods.map(rp => {
        const point = { returnPeriod: rp };
        for (const duration in idfData) {
          const val = idfData[duration][rp];
          if (val !== null && val !== undefined) {
            point[duration] = +val.toFixed(2);
          }
        }
        return point;
      });
      setChartData(formatted);
    }
  }, [idfData]);

  const handleDownload = async () => {
    const canvas = await html2canvas(chartRef.current);
    const link = document.createElement('a');
    link.download = 'idf_chart.png';
    link.href = canvas.toDataURL();
    link.click();
  };

  if (!chartData.length) return <p className="text-sm text-gray-500">No IDF data available.</p>;

  const colors = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#00bcd4', '#a83279'];

  return (
    <div className="mt-4">
      <div ref={chartRef} className="p-4 bg-white rounded shadow">
        <h4 className="font-semibold mb-2 text-gray-800">📈 IDF Curve (Intensity in mm/hr)</h4>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="returnPeriod" />
            <YAxis label={{ value: 'Intensity (mm/hr)', angle: -90, position: 'insideLeft' }} />
            <Tooltip />
            <Legend />
            {Object.keys(idfData).map((duration, i) => (
              <Line
                key={duration}
                type="monotone"
                dataKey={duration}
                stroke={colors[i % colors.length]}
                dot={{ r: 3 }}
                activeDot={{ r: 6 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <button
        onClick={handleDownload}
        className="mt-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        📥 Download Chart as PNG
      </button>
    </div>
  );
}

export default IdfViewer;

