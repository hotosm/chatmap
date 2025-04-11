import { createContext, useContext, useReducer } from 'react';

const MapDataContext = createContext();

// Initial state
const initialState = {
  type: "FeatureCollection",
  features: [],
  filterTag: null,
};

// Reducer
const reducer = (state, action) => {
  switch (action.type) {
    case 'set':
      return { ...state, ...action.payload };

    case 'update_feature_props': {
      const newState = { ...state };
      newState.features.forEach((feature) => {
        if (feature.properties.id === action.payload.id) {
          feature.properties = action.payload.properties;
        }
      });
      return newState;
    }

    case 'set_filter_tag':
      return { ...state, ...{filterTag: action.payload.tag } };

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
