import { lazy, useState, useEffect } from 'react';
import useFileManager from '../../components/FileUpload/useFileManager.js';
import useContentMerger from '../../components/ChatMap/useContentMerger.js';
import Header from '../header.jsx';
import Footer from '../footer.jsx';
import FileUploadSection from './fileUpload.section.jsx';
import NoLocationsSection from './noLocations.section.jsx';
import { useMapDataContext } from '../../context/MapDataContext.jsx';
import Messages from '../../components/Messages/index.jsx';

const Map = lazy(() => import('../../components/Map/index.jsx'));

function App() {

  const [noLocations, setNoLocations] = useState(false);
  const [selectedFeature, setSelectedFeature] = useState();
  const [showMessages, setShowMessages] = useState(false)

  // File Manager: Manages files and data files.
  // - handleFiles: handle all chat files
  // - handleDataFile: handle all other files (images, videos)
  // - resetFileManager: clear files and data files states
  // - files: stores all chat files
  // - dataFiles: stores all other files (images, videos)
  const [handleFiles, handleDataFile, resetFileManager, dataFiles, files] = useFileManager();

  // Content Merger: Handle chat content
  // - mapData: ready to use GeoJSON data created from chats
  // - messages: all chat messages
  // - resetMerger: clean everthing to upload a new file
  // TODO: return messages
  const [mapData, chatMessages, resetMerger] = useContentMerger({
    files: files
  });
  

  useEffect(() => {
      setShowMessages(false);
  }, [mapData])

  // Map Data Context: Manages map data
  const { data, mapDataDispatch } = useMapDataContext();

  // Updates map data context with new map data
  useEffect(() => {
    mapDataDispatch({
      type: 'set',
      payload: mapData,
    });
  }, [mapData]);

  // The user wants to upload a new file, clear everything
  // (files, map data, errors)
  const handleNewUploadClick = () => {
    resetFileManager();
    resetMerger();
    setNoLocations(false);
    setSelectedFeature()
  }

  // Click header navigation option (ex: show/hide chat)
  const handleOptionClick = option => {
    if (option === "chat") {
      setShowMessages(prev => !prev);
    }
  }

  // Handle uploaded files error (ex: invalid chat export)
  const handleFilesError = () => {
    setNoLocations(true);
  }

  // There's data for the map!
  const dataAvailable = files && data && data.features && data.features.length > 0;

  const handleFeatureSelect = (feature) => {
    setSelectedFeature(feature.properties);
  }

  return (
    <div className="app">

        <Header
          dataAvailable={dataAvailable}
          dataFiles={dataFiles}
          mapData={data}
          handleNewUploadClick={handleNewUploadClick}
          handleOptionClick={handleOptionClick}
          showUploadButton={true}
        />

        { showMessages && dataAvailable &&
          <Messages
            messages={chatMessages}
            dataFiles={dataFiles}
            selectedFeature={selectedFeature} 
          />
        }

        {/* If there're no files, show file upload options */}
        { !files &&
          <>
            <FileUploadSection
              handleFiles={handleFiles}
              handleDataFile={handleDataFile}
              onError={handleFilesError}
            />
            <Footer />
          </>
        }

        {/* There's data, show the map! */}
        { dataAvailable && 
          <Map 
            data={data}
            dataFiles={dataFiles}
            onSelectFeature={handleFeatureSelect}
          />
        }

        {/* If there are no locations, show a message */}
        { noLocations && 
          <NoLocationsSection
            handleNewUploadClick={handleNewUploadClick}
          />
        }
    </div>
  );
}

export default App;
