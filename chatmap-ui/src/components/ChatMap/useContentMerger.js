import { useEffect, useState } from "react";
import getAppParser from "./parsers/getAppParser";

/**
 * Hook for parsing messages from a text
 *
 * This is where the magic happens!  ・• * . ☆ﾟ
 *
 * @param {object} files - Is a dictionary of files, filename 
 * is the key ex: myfile = files[filename]
 * (empty for default) to each location.
 */
function useContentMerger({ files, options }) {

    // Hook's response: a GeoJSON object
    const [geoJSON, setGeoJSON] = useState({
        type: "FeatureCollection",
        features: [],
        _sources: [],
    });

    // Receives files and update status
    // with a GeoJSON response and messages
    useEffect(() => {
        async function parseData() {
            // If no files provided, return
            if (!files) return;

            // Parse each file and concatate the results
            // This way, multiple .zip files with multiple chats
            // can be imported.
            let features = [];
            let _chatmapId = null;
            const sources = [];

            for (let filename in files) {
                // Parse data from chats with the corresponding parser
                // depending on the chat app (ex: WhatsApp, Telegram or Signal)
                const parser = await getAppParser(files[filename]);

                if (sources.indexOf(parser._name) === -1) {
                    sources.push(parser._name);
                }

                // Concatenate data from all uploaded chats
                const {geoJSON} = parser({ text: files[filename], options });
                if (geoJSON._chatmapId) {
                    _chatmapId = geoJSON._chatmapId;
                }
                features = features.concat(geoJSON.features);
            }

            // Build the GeoJSON response with all features
            setGeoJSON((prevState) => {
                const newSources = prevState._sources;

                for (let source of sources) {
                    if (newSources.indexOf(source) === -1) {
                        newSources.push(source);
                    }
                }

                return {
                    type: "FeatureCollection",
                    features: [...prevState.features, ...features],
                    _chatmapId: _chatmapId || null,
                    _sources: newSources,
                };
            });
        }

        parseData();
      }, [files]);

    // It resets data, initializing with an empty GeoJSON object.
    const resetMerger = () => {
        setGeoJSON({
            type: "FeatureCollection",
            features: []
        });
    }

    return [geoJSON, resetMerger];

};

export default useContentMerger;
