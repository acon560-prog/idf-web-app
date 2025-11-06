// File: src/pages/AdminDashboard.jsx
import React, { useEffect, useMemo, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { buildApiUrl, readJsonResponse } from "../utils/apiConfig";

function AdminDashboard() {
  const { user, authFetch } = useAuth();
  const location = useLocation();
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const contactApiUrl = useMemo(() => buildApiUrl("/contact"), []);

  useEffect(() => {
    if (!user || user.role !== "admin") {
      setLoading(false);
      return;
    }

    const controller = new AbortController();

    const fetchSubmissions = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await (authFetch
          ? authFetch(contactApiUrl, { signal: controller.signal })
          : fetch(contactApiUrl, { signal: controller.signal }));

        if (response.status === 403) {
          setError("You do not have permission to view submissions.");
          setSubmissions([]);
          return;
        }

        const data = await readJsonResponse(
          response,
          "Failed to load submissions.",
        );
        if (!response.ok) {
          throw new Error(data?.error || "Failed to load submissions.");
        }
        setSubmissions(Array.isArray(data) ? data : []);
      } catch (err) {
        if (err.name === "AbortError") return;
        console.error("Failed to fetch submissions", err);
        const apiHint = contactApiUrl ? ` (API: ${contactApiUrl})` : "";
        setError(
          err.message
            ? `${err.message}${apiHint}`
            : `Unexpected error while loading submissions.${apiHint}`,
        );
      } finally {
        setLoading(false);
      }
    };

    fetchSubmissions();

    return () => controller.abort();
  }, [authFetch, contactApiUrl, user]);

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (user.role !== "admin") {
    return <Navigate to="/" replace />;
  }

  const downloadCSV = () => {
    const headers = ["Name", "Email", "Message", "Date"];
    const rows = submissions.map((submission) => [
      submission.name,
      submission.email,
      submission.message,
      submission.date ? new Date(submission.date).toLocaleString() : "",
    ]);

    const csvContent = [
      headers.join(","),
      ...rows.map((row) =>
        row
          .map((field) => {
            const value = field ?? "";
            return `"${String(value).replace(/"/g, '""')}"`;
          })
          .join(","),
      ),
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "submissions.csv";
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold">Admin Dashboard</h2>
        <button
          onClick={downloadCSV}
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={submissions.length === 0}
          type="button"
        >
          Export CSV
        </button>
      </div>

      {loading && <p className="text-gray-500">Loading submissions…</p>}

      {error && !loading && <p className="text-red-600 mb-4">{error}</p>}

      {!loading && !error && (
        <div className="overflow-x-auto">
          <table className="min-w-full bg-white border border-gray-200">
            <thead className="bg-gray-100">
              <tr>
                <th className="border px-4 py-2 text-left">Name</th>
                <th className="border px-4 py-2 text-left">Email</th>
                <th className="border px-4 py-2 text-left">Message</th>
                <th className="border px-4 py-2 text-left">Date</th>
              </tr>
            </thead>
            <tbody>
              {submissions.map((submission) => (
                <tr
                  key={
                    submission._id || `${submission.email}-${submission.date}`
                  }
                  className="hover:bg-gray-50"
                >
                  <td className="border px-4 py-2">{submission.name}</td>
                  <td className="border px-4 py-2">{submission.email}</td>
                  <td className="border px-4 py-2 whitespace-pre-wrap">
                    {submission.message}
                  </td>
                  <td className="border px-4 py-2">
                    {submission.date
                      ? new Date(submission.date).toLocaleString()
                      : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {submissions.length === 0 && (
            <p className="text-center text-gray-500 mt-4">
              No submissions found.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default AdminDashboard;
