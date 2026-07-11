// import React, { useState } from 'react';
// import URLShortener from './components/URLShortener';
// import Analytics from './components/Analytics';
// import './styles/App.css';

// function App() {
//   const [activeTab, setActiveTab] = useState('shorten');

//   return (
//     <div className="app">
//       <div className="tabs">
//         <button
//           className={`tab ${activeTab === 'shorten' ? 'active' : ''}`}
//           onClick={() => setActiveTab('shorten')}
//         >
//           🔗 Shorten URL
//         </button>
//         <button
//           className={`tab ${activeTab === 'analytics' ? 'active' : ''}`}
//           onClick={() => setActiveTab('analytics')}
//         >
//           📊 Analytics
//         </button>
//       </div>

//       {activeTab === 'shorten' ? <URLShortener /> : <Analytics />}

//       <footer style={{ textAlign: 'center', marginTop: '2rem', color: 'rgba(255,255,255,0.8)' }}>
//         <p>Built with ❤️ using FastAPI & React</p>
//       </footer>
//     </div>
//   );
// }

// export default App;


import React, { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import URLShortener from './components/URLShortener';
import Analytics from './components/Analytics';
import RedirectHandler from './components/RedirectHandler';
import './styles/App.css';

const MainApp = () => {
  const [activeTab, setActiveTab] = useState('shorten');

  return (
    <div className="app">
      <div className="tabs">
        <button
          className={`tab ${activeTab === 'shorten' ? 'active' : ''}`}
          onClick={() => setActiveTab('shorten')}
        >
          🔗 Shorten URL
        </button>
        <button
          className={`tab ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => setActiveTab('analytics')}
        >
          📊 Analytics
        </button>
      </div>
      {activeTab === 'shorten' ? <URLShortener /> : <Analytics />}
      <footer style={{ textAlign: 'center', marginTop: '2rem', color: 'rgba(255,255,255,0.8)' }}>
        <p>Built with ❤️ using FastAPI & React</p>
      </footer>
    </div>
  );
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Short code redirect — checked first before falling through to main UI */}
        <Route path="/:shortCode" element={<RedirectHandler />} />
        {/* Main app UI */}
        <Route path="/*" element={<MainApp />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;