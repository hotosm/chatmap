import { useEffect, useState } from "react";
import getAppParser from "../parsers/detectApp";

/**
 * Hook for parsing messages from a text
 *
 * @param {object} files - Is a dictionary of files, filename is the key ex: myfile = files[filename]
 * @param {string} msgPosition - Parser config. Content to attach is "before", "after" or "closest"
 * (empty for default) to each location.
 */
function useContentMerger({ files, msgPosition}) {

    // Hook's response: a GeoJSON object
    const [geoJSON, setGeoJSON] = useState({
        type: "FeatureCollection",
        features: []
    });

    // Receives files and update status
    // with a GeoJSON response
    useEffect(() => {
        // If no files provided, return
        if (!files) return;

        // Parse each file and concatate the results
        // This way, multiple .zip files with multiple chats
        // can be imported.
        let features = [];
        for (let filename in files) {

            // Parse data from chats. This is where the magic happens!  ・• * . ☆ﾟ
            const parser = getAppParser(files[filename]);

            // Concatenate data from all uploaded chats
            const parsedData = parser({ text: files[filename], msgPosition });
            features = features.concat(parsedData.features);
        }

        // Build the GeoJSON response with all features
        setGeoJSON((prevState) => ({
            type: "FeatureCollection",
            features: [...prevState.features, ...features]
        }));

      }, [files]);

    // It resets data, initializing with an empty GeoJSON object.
    const resetMerger = () => {
        setGeoJSON({
            type: "FeatureCollection",
            features: []
        })
    }

    return [geoJSON, resetMerger];

};

export default useContentMerger;
