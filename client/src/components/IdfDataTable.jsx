// File: civil-eng-website/client/src/components/IdfDataTable.jsx

import React from 'react';

const IdfDataTable = ({ idfData }) => {
  if (!idfData || !Array.isArray(idfData) || idfData.length === 0) {
    return null;
  }

  const returnPeriods = ['2', '5', '10', '25', '50', '100'];

  return (
    <div className="bg-white rounded-lg shadow p-4 mt-8">
      <h4 className="text-lg font-semibold mb-4 text-center text-blue-700">
        Precipitation Intensities (mm/hr)
      </h4>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                Duration
              </th>
              {returnPeriods.map((rp) => (
                <th
                  key={rp}
                  scope="col"
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  {`${rp}-year RP`}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {idfData.map((dataPoint) => (
              <tr key={dataPoint.duration}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {dataPoint.duration < 60 ? `${dataPoint.duration} min` : `${dataPoint.duration / 60} hr`}
                </td>
                {returnPeriods.map((rp) => (
                  <td key={rp} className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {dataPoint[rp]?.toFixed(2)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default IdfDataTable;