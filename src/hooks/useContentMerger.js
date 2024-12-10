import { useEffect, useState } from "react";

// Hook for parsing messages from a text
function usefilesMerger({ files, msgPosition, parser}) {

    const [geoJSON, setGeoJSON] = useState({
        type: "FeatureCollection",
        features: []
    });

    useEffect(() => {
        if (!files) return;
        let features = [];
        for (let filename in files) {
            const parsedData = parser({ text: files[filename], msgPosition });
            features = features.concat(parsedData.features);
        }
        setGeoJSON((prevState) => ({
            type: "FeatureCollection",
            features: [...prevState.features, ...features]
        }));
    
      }, [files]);

    const resetMerger = () => {
        setGeoJSON({
            type: "FeatureCollection",
            features: []    
        })
    }

    return [geoJSON, resetMerger];

};

export default usefilesMerger;
