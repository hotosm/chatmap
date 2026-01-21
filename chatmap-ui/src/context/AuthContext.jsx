import { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(undefined);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [osmConnection, setOsmConnection] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Listen to hanko-login event from web component
    // The web component handles session verification with correct cookie options
    const handleLogin = (event) => {
      setUser(event.detail.user);
      setLoading(false);
    };

    // Listen to logout event from web component
    const handleLogout = () => {
      setUser(null);
      setOsmConnection(null);
    };

    // Listen to osm-connected event from web component
    const handleOsmConnected = (event) => {
      setOsmConnection(event.detail.osmData);
    };

    // Add event listeners
    document.addEventListener('hanko-login', handleLogin);
    document.addEventListener('logout', handleLogout);
    document.addEventListener('osm-connected', handleOsmConnected);

    // Set a timeout to stop loading if no login event is received
    // This handles the case where user is not logged in
    const timeout = setTimeout(() => {
      setLoading(false);
    }, 1500);

    // Cleanup
    return () => {
      document.removeEventListener('hanko-login', handleLogin);
      document.removeEventListener('logout', handleLogout);
      document.removeEventListener('osm-connected', handleOsmConnected);
      clearTimeout(timeout);
    };
  }, []);

  const value = {
    user,
    osmConnection,
    isAuthenticated: user !== null,
    loading,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
