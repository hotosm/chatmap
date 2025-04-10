import { createContext, useContext, useReducer } from 'react';

const MapDataContext = createContext();

// Initial state
const initialState = {
  type: "FeatureCollection",
  features: []
};

// Reducer
const reducer = (state, action) => {
  switch (action.type) {
    case 'set':
      return { ...state, ...action.payload };

    case 'add_tag': {
      const newState = { ...state };
      newState.features.forEach((feature) => {
        if (feature.properties.id === action.payload.id) {
          if (!feature.properties.tags) {
            feature.properties.tags = {};
          }
          feature.properties.tags[action.payload.tag_key] = action.payload.tag_value;
        }
      });
      return newState;
    };

    case 'remove_tag': {
      const newState = { ...state };
      newState.features.forEach((feature) => {
        if (feature.properties.id === action.payload.id) {
          delete feature.properties.tags[action.payload.tag_key];
        }
      });
      return newState;
    };
    default:
      throw new Error();
  }
}

// Provider
export const MapDataProvider = (props) => {
  const [data, mapDataDispatch] = useReducer(reducer, initialState);

  return (
    <MapDataContext.Provider value={{ data, mapDataDispatch }}>
      {props.children}
    </MapDataContext.Provider>
  );
}

// Hook
export const useMapDataContext = () => {
  return useContext(MapDataContext);
}
