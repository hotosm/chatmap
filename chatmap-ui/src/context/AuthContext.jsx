import { createContext, useContext, useState, useEffect } from 'react';
import { Hanko } from '@teamhanko/hanko-elements';

const AuthContext = createContext(undefined);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [osmConnection, setOsmConnection] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing session on mount (handles page refresh)
    const checkExistingSession = async () => {
      try {
        const hankoUrl = import.meta.env.VITE_HANKO_URL;
        if (hankoUrl) {
          const hanko = new Hanko(hankoUrl);
          const currentUser = await hanko.user.getCurrent();
          if (currentUser) {
            console.log('AuthContext: existing session found', currentUser);
            setUser(currentUser);
          }
        }
      } catch (e) {
        console.log('AuthContext: no existing session');
      } finally {
        setLoading(false);
      }
    };

    checkExistingSession();

    // Listen to hanko-login event from web component
    const handleLogin = (event) => {
      console.log('AuthContext: hanko-login event received', event.detail);
      setUser(event.detail.user);
    };

    // Listen to logout event from web component
    const handleLogout = () => {
      console.log('AuthContext: logout event received');
      setUser(null);
      setOsmConnection(null);
    };

    // Listen to osm-connected event from web component
    const handleOsmConnected = (event) => {
      console.log('AuthContext: osm-connected event received', event.detail);
      setOsmConnection(event.detail.osmData);
    };

    // Add event listeners
    document.addEventListener('hanko-login', handleLogin);
    document.addEventListener('logout', handleLogout);
    document.addEventListener('osm-connected', handleOsmConnected);

    // Cleanup
    return () => {
      document.removeEventListener('hanko-login', handleLogin);
      document.removeEventListener('logout', handleLogout);
      document.removeEventListener('osm-connected', handleOsmConnected);
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
