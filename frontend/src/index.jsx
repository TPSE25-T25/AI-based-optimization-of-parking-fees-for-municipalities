import React from 'react';

// used to render React components into the browser's DOM (Document Object Model)
import ReactDOM from 'react-dom/client';

import './index.css';

// Import the main App component, this is the root component of our application
import App from './components/App/App';

// Create a "root" element where our React app will be mounted
// This finds the HTML element with id="root" in public/index.html
const root = ReactDOM.createRoot(document.getElementById('root'));

// Render our App component into the root element
root.render(
  // StrictMode is a React tool that helps catch potential problems during development
  // It runs extra checks and warnings but doesn't affect production builds
  <React.StrictMode>
    <App />
  </React.StrictMode>
);