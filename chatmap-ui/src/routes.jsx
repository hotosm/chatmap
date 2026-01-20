// App.tsx (or wherever you want to keep the routing logic)
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import Home from './pages/home';
import Linked from './pages/linked';
import LoginPage from './pages/login';
import MapView from './pages/mapView';
import { useConfigContext } from './context/ConfigContext.jsx';

const PrivateRoute = ({ children }) => {
  const { isAuthenticated } = useAuth();
  const { config } = useConfigContext();

  if (isAuthenticated) {
    return children;
  }

  // Strip everything up to the hash
  const hashIndex = config.LOGIN_URL.indexOf("#");
  const relativePath = hashIndex >= 0 ? config.LOGIN_URL.slice(hashIndex + 1) : config.LOGIN_URL;
  return <Navigate to={relativePath} replace />;

};

const AppRoutes = () => {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/app" element={<LoginPage />} />
      <Route path="/map/:id" element={<MapView />} />
      <Route
           path="/linked"
           element={<PrivateRoute><Linked /></PrivateRoute>}
      />
    </Routes>
  );
};

export default AppRoutes;