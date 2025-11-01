import React from 'react';

function Footer() {
    // return <div style={{ backgroundColor: 'blue', color: 'white' }}>FOOTER TEST</div>;
  return (
    <footer className="bg-gray-100 text-center p-4 text-sm text-gray-600">
      <p>&copy; {new Date().getFullYear()} CiviSpec. All rights reserved.</p>
    </footer>
  );
}

export default Footer;