import { createContext, useContext, useReducer } from 'react';

const MapDataContext = createContext();

// Initial state
const initialState = {
  type: "FeatureCollection",
  features: [],
  filterTag: null,
  filterDate: null,
  _chatmapId: null
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
          feature.properties.time = new Date(feature.properties.time);
        }
      });
      return newState;
    }

    case 'set_filter_tag':
      return { ...state, ...{filterTag: action.payload.tag } };

    case 'set_filter_date':
      return { ...state, ...{filterDate: action.payload.date } };

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

  const indexedData = {
    ...data,
    features: data.features.map( (feature, index) => {
      return {
        ...feature,
        properties: {
          ...feature.properties,
          index: index
        }
      }
    })
  }

  return (
    <MapDataContext.Provider value={{ data: indexedData, tags, mapDataDispatch }}>
      {props.children}
    </MapDataContext.Provider>
  );
}

// Hook
export const useMapDataContext = () => {
  return useContext(MapDataContext);
}
