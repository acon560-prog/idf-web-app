import React from "react";

const Card = ({ className = "", children }) => (
  <div
    className={`rounded-2xl border border-slate-200 bg-white p-8 shadow-sm ${className}`}
  >
    {children}
  </div>
);

export default Card;
