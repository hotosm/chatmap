import { createContext, useContext, useReducer } from 'react';

const MapDataContext = createContext();

// Initial state
const initialState = {
  type: "FeatureCollection",
  features: [],
  filterTag: null,
  hasChanged: false,
  _chatmapId: null,
  _sources: []
};

// Reducer
const reducer = (state, action) => {
  switch (action.type) {
    case 'set':
      return { ...state, ...action.payload };

    case 'update_feature_props': {
      const newState = { ...state, ...{ hasChanged: true } };
      newState.features.forEach((feature) => {
        if (feature.properties.id === action.payload.id) {
          feature.properties = action.payload.properties;
        }
      });
      return newState;
    }

    case 'set_filter_tag':
      return { ...state, ...{filterTag: action.payload.tag}};

    case 'reset':
      return { ...initialState };

    default:
      throw new Error();
  }
}

// Provider
export const MapDataProvider = (props) => {

  const [data, mapDataDispatch] = useReducer(reducer, initialState);

  const tags = data.features.reduce((accumulator, currentValue) => {
      if (currentValue.properties.tags) {
          currentValue.properties.tags.forEach(tag => {
              accumulator[tag] = (accumulator[tag] || 0) + 1;
          });
      }
      return accumulator;
  }, {});

  return (
    <MapDataContext.Provider value={{ data, tags, mapDataDispatch }}>
      {props.children}
    </MapDataContext.Provider>
  );
}

// Hook
export const useMapDataContext = () => {
  return useContext(MapDataContext);
}
