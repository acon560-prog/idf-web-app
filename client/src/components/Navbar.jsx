import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { user, logout } = useAuth();
  const isAdmin = user?.role === "admin";

  return (
    <nav className="bg-gray-800 text-white">
      <div className="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
        <h1 className="text-xl font-bold">CiviSpec</h1>

        <ul className="hidden md:flex space-x-6 items-center">
          <li><Link to="/" className="hover:underline">Home</Link></li>
          <li><Link to="/about" className="hover:underline">About</Link></li>
          <li><Link to="/services" className="hover:underline">Services</Link></li>
          <li><Link to="/contact" className="hover:underline">Contact</Link></li>
          {isAdmin && (
            <li><Link to="/admin" className="hover:underline">Admin</Link></li>
          )}
          <li><Link to="/start" className="hover:underline text-yellow-300 font-semibold">Start</Link></li>
          {user && (
            <li>
              <button
                type="button"
                onClick={logout}
                className="hover:underline"
              >
                Log out
              </button>
            </li>
          )}
        </ul>

        <button
          className="md:hidden text-white focus:outline-none"
          onClick={() => setMenuOpen(!menuOpen)}
        >
          ☰
        </button>
      </div>

      {menuOpen && (
        <ul className="md:hidden px-4 pb-4 space-y-2 bg-gray-700">
          <li><Link to="/" onClick={() => setMenuOpen(false)}>Home</Link></li>
          <li><Link to="/about" onClick={() => setMenuOpen(false)}>About</Link></li>
          <li><Link to="/services" onClick={() => setMenuOpen(false)}>Services</Link></li>
          <li><Link to="/contact" onClick={() => setMenuOpen(false)}>Contact</Link></li>
          {isAdmin && (
            <li><Link to="/admin" onClick={() => setMenuOpen(false)}>Admin</Link></li>
          )}
          <li><Link to="/start" onClick={() => setMenuOpen(false)} className="text-yellow-300 font-semibold">Start</Link></li>
          {user && (
            <li>
              <button
                type="button"
                onClick={() => {
                  logout();
                  setMenuOpen(false);
                }}
                className="hover:underline"
              >
                Log out
              </button>
            </li>
          )}
        </ul>
      )}
    </nav>
  );
}

export default Navbar;
