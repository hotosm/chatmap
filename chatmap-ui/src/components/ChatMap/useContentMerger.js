import { useEffect, useState } from "react";
import getAppParser from "./parsers/getAppParser";
import { createChatMapId } from "../ChatMap/chatmap";
import ChatMap from "../ChatMap/chatmap";

/**
 * Hook for parsing messages from a text
 *
 * This is where the magic happens!  ・• * . ☆ﾟ
 *
 * @param {object} files - Is a dictionary of files, filename 
 * is the key ex: myfile = files[filename]
 * (empty for default) to each location.
 */
function useContentMerger({ files, withPhotos, withVideos, withAudios, withText }) {

    // Hook's response: a GeoJSON object
    const [parsedChats, setParsedChats] = useState([]);
    const [geoJSON, setGeoJSON] = useState({
        type: "FeatureCollection",
        features: [],
        _sources: [],
    });

    // Receives files and update status
    // with a GeoJSON response and messages
    useEffect(() => {
        async function parseData() {
            if (!files) return;

            // Parse each file and concatate the results
            // This way, multiple .zip files with multiple chats
            // can be imported.
            const sources = [];
            const allChats = []; // Collection of all parsed messages from all chats

            for (let filename in files) {
                // Parse data from chats with the corresponding parser
                // depending on the chat app (ex: WhatsApp, Telegram or Signal)
                const {parser, searchLocation} = await getAppParser(files[filename]);

                if (sources.indexOf(parser._name) === -1) {
                    sources.push(parser._name);
                }

                const messages = parser({ text: files[filename] });
                allChats.push({ messages, searchLocation, sources });
            }

            setParsedChats(allChats);
        }

        parseData();
    }, [files])

    // Attach media to locations based on user preferences.
    useEffect(() => {
      let features = [];
      const sources = [];

      for (let {messages, searchLocation, sources: localSources} of parsedChats) {
        const chatmap = new ChatMap(messages);
        const geoJSON = chatmap.pairContentAndLocations(searchLocation, {
          withPhotos, withVideos, withAudios, withText,
        });

        features = features.concat(geoJSON.features);

        for (let source of localSources) {
          if (sources.indexOf(source) !== -1) {
            sources.push(source);
          }
        }
      }

      // Build the GeoJSON response with all features
      setGeoJSON({
        type: "FeatureCollection",
        features,
        _chatmapId: createChatMapId(),
        _sources: sources,
      });
    }, [parsedChats, withPhotos, withVideos, withAudios, withText]);

    // It resets data, initializing with an empty GeoJSON object.
    const resetMerger = () => {
        setGeoJSON({
            type: "FeatureCollection",
            features: [],
            _sources: [],
        });
    }

    return [geoJSON, resetMerger];

};

export default useContentMerger;
