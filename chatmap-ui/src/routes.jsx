import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Home from './pages/home';
import Linked from './pages/linked';
import LoginPage from './pages/login';
import MapView from './pages/mapView';
import { useConfigContext } from './context/ConfigContext.jsx';
import '@hotosm/hanko-auth';

const PrivateRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  const { config } = useConfigContext();

  // Wait for session check to complete
  if (loading) {
    return <div>Loading...</div>;
  }

  if (isAuthenticated) {
    return children;
  }

  // If LOGIN_URL is external, redirect via browser with return_to param
  if (config.LOGIN_URL.startsWith('http')) {
    const returnTo = encodeURIComponent(window.location.href);
    window.location.href = `${config.LOGIN_URL}?return_to=${returnTo}`;
    return null;
  }

  // If internal route (hash-based), use React Router
  const hashIndex = config.LOGIN_URL.indexOf("#");
  const relativePath = hashIndex >= 0 ? config.LOGIN_URL.slice(hashIndex + 1) : config.LOGIN_URL;
  return <Navigate to={relativePath} replace />;
};

// Hidden session verifier - renders the web component to check session
// and dispatch hanko-login event, but doesn't show any UI
const SessionVerifier = () => {
  const { config } = useConfigContext();

  if (!config?.HANKO_API_URL) return null;

  return (
    <div style={{ display: 'none' }}>
      <hotosm-auth
        hanko-url={config.HANKO_API_URL}
      />
    </div>
  );
};

const AppRoutes = () => {
  const { config } = useConfigContext();
  return (
    <>
      { config.ENABLE_AUTH &&
        <SessionVerifier />
      }
      <Routes>
        <Route path="/" element={<Home />} />

        { config.ENABLE_LIVE && config.ENABLE_AUTH && <>
        <Route path="/app" element={<LoginPage />} />
        <Route path="/map/:id" element={<MapView />} />
        <Route
             path="/linked"
             element={<PrivateRoute><Linked /></PrivateRoute>}
        /> </>}

        { config.ENABLE_LIVE && !config.ENABLE_AUTH && <>
        <Route path="/app" element={<LoginPage />} />
        <Route path="/map/:id" element={<MapView />} />
        <Route
             path="/linked"
             element={<PrivateRoute><Linked /></PrivateRoute>}
        /> </>}

      </Routes>
    </>
  );
};

export default AppRoutes;