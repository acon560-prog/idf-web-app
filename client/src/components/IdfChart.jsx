// File: civil-eng-website/client/src/components/IdfChart.jsx

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import IdfDataTable from './IdfDataTable';

// Custom formatter for the X-Axis ticks on a log scale
const formatDuration = (tickItem) => {
  const duration = parseFloat(tickItem);
  if (isNaN(duration)) return 'N/A';
  if (duration === 0) return '0 min';
  if (duration < 60) return `${duration.toFixed(0)} min`;
  return `${(duration / 60).toFixed(0)} hr`;
};

// Custom Tooltip for better display
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="custom-tooltip bg-white p-2 border border-gray-300">
        <p className="label font-bold text-lg">{`Duration: ${formatDuration(label)}`}</p>
        {payload.map((p, index) => (
          <p key={index} style={{ color: p.color }}>
            {`${p.name}: ${p.value.toFixed(2)} mm/hr`}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

const IdfChart = ({ idfData, loading, error }) => {
  if (loading) {
    return <div className="text-center p-4">Loading IDF data...</div>;
  }

  if (error) {
    return (
      <div className="text-center p-4 text-red-500">
        Error: {error}
      </div>
    );
  }

  // **CRITICAL FIX: Conditional rendering to clear old data**
  if (!idfData || !Array.isArray(idfData) || idfData.length === 0) {
    return (
      <div className="text-center p-4 text-gray-500">
        No IDF data available for the selected station.
      </div>
    );
  }

  // Recalculate data to convert depth (mm) to intensity (mm/hr)
  const calculateIntensity = (data) => {
    return data.map(d => {
      const durationHours = d.duration / 60; // Convert duration from minutes to hours
      return {
        duration: d.duration,
        '100': d['100'] / durationHours,
        '50': d['50'] / durationHours,
        '25': d['25'] / durationHours,
        '10': d['10'] / durationHours,
        '5': d['5'] / durationHours,
        '2': d['2'] / durationHours,
      };
    });
  };

  const idfIntensityData = calculateIntensity(idfData);
  
  // Define the order and properties for the curves
  const returnPeriods = ['100', '50', '25', '10', '5', '2'];
  const colors = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#007bff', '#28a745'];
  const legendNames = [
    '100-year RP', '50-year RP', '25-year RP', '10-year RP', '5-year RP', '2-year RP'
  ];
  
  // Extract all unique duration values for ticks
  const durationTicks = [...new Set(idfIntensityData.map(d => d.duration))].sort((a, b) => a - b);
  const maxIntensity = Math.max(...idfIntensityData.flatMap(d => returnPeriods.map(rp => d[rp])));
  const yDomain = [0, maxIntensity * 1.2];

  return (
    <>
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-xl font-semibold mb-4 text-center text-blue-700">
          
        </h3>
        <ResponsiveContainer width="100%" height={400}>
          <LineChart
            data={idfIntensityData}
            margin={{
              top: 20,
              right: 30,
              left: 20,
              bottom: 5,
            }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="duration"
              type="number"
              scale="log"
              label={{ value: 'Duration (min)', position: 'insideBottom', offset: 0 }}
              tickFormatter={formatDuration}
              ticks={durationTicks}
            />
            <YAxis
              label={{ value: 'Intensity (mm/hr)', angle: -90, position: 'insideLeft' }}
              domain={yDomain}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              layout="horizontal"
              verticalAlign="bottom"
              align="center"
              wrapperStyle={{ paddingTop: '20px' }}
            />
            
            {/* Explicitly rendering lines in the correct order (highest RP first) */}
            {returnPeriods.map((rp, index) => (
              <Line
                key={rp}
                type="monotone"
                dataKey={rp}
                stroke={colors[index]}
                name={legendNames[index]}
                dot={true}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <IdfDataTable idfData={idfIntensityData} />
    </>
  );
};

export default IdfChart;