// MapDataContext.jsx
import { createContext, useContext, useReducer } from 'react';

// Create a context to hold the state
const MapDataContext = createContext();

// Define the initial state
const initialState = {
  type: "FeatureCollection",
  features: []
};

// Define the reducer function to handle state transitions
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

// Create a component that will provide the context
// MapDataProvider takes in an argument called children
export const MapDataProvider = (props) => {
  const [data, mapDataDispatch] = useReducer(reducer, initialState);

  return (
    <MapDataContext.Provider value={{ data, mapDataDispatch }}>
      {props.children}
    </MapDataContext.Provider>
  );
}

// Create a function that invokes the context 
export const useMapDataContext = () => {
  return useContext(MapDataContext);
}
