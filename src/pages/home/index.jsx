import React, { lazy, useState } from 'react';
import useSettings from '../../components/Settings/useSettings.js';
import useFileManager from '../../components/FileUpload/useFileManager.js';
import useContentMerger from '../../components/ChatMap/useContentMerger.js';
import Header from '../header.jsx';
import Footer from '../footer.jsx';
import FileUploadSection from './fileUpload.section.jsx';
import NoLocationsSection from './noLocations.section.jsx';

const Map = lazy(() => import('../../components/Map/index.jsx'));

function App() {

  const [noLocations, setNoLocations] = useState(false);

  // Manage settings
  // - settings: store settings
  // - handleSettingsChange: update settings after changes
  const [settings, handleSettingsChange] = useSettings({
    msgPosition: "closest"
  });

  // Manage files and data files.
  // - handleFiles: handle all chat files
  // - handleDataFile: handle all other files (images, videos)
  // - resetFileManager: clear files and data files states
  // - files: stores all chat files
  // - dataFiles: stores all other files (images, videos)
  const [handleFiles, handleDataFile, resetFileManager, dataFiles, files] = useFileManager();

  // It will receive chat files, parse them depending on the chat app
  // and update the final data for the map.
  // - mapData: contains the GeoJSON data for the map
  // - resetMerger: will clear the data with an empty GeoJSON
  const [mapData, resetMerger] = useContentMerger({
    files: files,
    msgPosition: settings.msgPosition
  });

  // The user wants to upload a new file, clear everything
  // (files, map data, errors)
  const handleNewUploadClick = () => {
    resetFileManager()
    resetMerger();
    setNoLocations(false);
  }

  // Handle uploaded files error (ex: invalid chat export)
  const handleFilesError = () => {
    setNoLocations(true);
  }

  // There's data for the map!
  const dataAvailable = files && mapData.features.length > 0;

  return (
    <div className="app">

      <Header
        dataAvailable={dataAvailable}
        dataFiles={dataFiles}
        mapData={mapData}
        handleNewUploadClick={handleNewUploadClick}
        settings={settings}
        handleSettingsChange={handleSettingsChange}
      />

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

      {/* If there's data available, show the map! */}
      { dataAvailable && 
        <Map data={mapData} dataFiles={dataFiles}/>
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
