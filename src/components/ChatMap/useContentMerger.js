import { useEffect, useState } from "react";
import getAppParser from "./parsers/getAppParser";
import { createChatMapId } from "../ChatMap/chatmap";

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
        features: []
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
            
            for (let filename in files) {
                // Parse data from chats with the corresponding parser
                // depending on the chat app (ex: WhatsApp, Telegram or Signal)
                const parser = await getAppParser(files[filename]);

                // Concatenate data from all uploaded chats
                const {geoJSON} = parser({ text: files[filename], options });
                if (geoJSON._chatmapId) {
                    _chatmapId = geoJSON._chatmapId;
                }
                features = features.concat(geoJSON.features);
            }

            // Build the GeoJSON response with all features
            setGeoJSON((prevState) => ({
                type: "FeatureCollection",
                features: [...prevState.features, ...features],
                _chatmapId: _chatmapId || createChatMapId()
            }));

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
