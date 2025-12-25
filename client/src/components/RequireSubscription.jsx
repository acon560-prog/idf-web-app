import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

function RequireSubscription({ children }) {
  const { user } = useAuth();
  const location = useLocation();

  const hasAccess =
    user?.role === "admin" || user?.subscriptionStatus === "active";

  if (!hasAccess) {
    return <Navigate to="/start" replace state={{ from: location }} />;
  }

  return children;
}

export default RequireSubscription;
