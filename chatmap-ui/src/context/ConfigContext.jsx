import { createContext, useContext, useReducer, useEffect } from 'react';

const ConfigContext = createContext();

// Reducer
const configReducer = (state, action) => {
    switch (action.type) {
    case 'SET_CONFIG':
      return { ...state, config: action.payload, loading: false };
    case 'SET_ERROR':
      return { ...state, error: action.error, loading: false };
    case 'START_LOADING':
      return { ...state, loading: true };
    case 'STOP_LOADING':
      return { ...state, loading: false };
    default:
      return state;
  }
}

// Provider
export function ConfigProvider({ children, initialConfig }) {
  const [state, dispatch] = useReducer(configReducer, {
    config: initialConfig || null,
    loading: !initialConfig,
    error: null
  });

  useEffect(() => {
    if (initialConfig) return;
  }, [initialConfig]);

  return (
    <ConfigContext.Provider
      value={{
        config: state.config,
        configDispatch: dispatch,
        loading: state.loading,
        error: state.error
      }}
    >
      {children}
    </ConfigContext.Provider>
  );
}

// Context
export const useConfigContext = () => {
  const ctx = useContext(ConfigContext);
  if (!ctx) {
    throw new Error('useConfig must be used inside a ConfigProvider');
  }
  return ctx;
}
