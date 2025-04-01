import React, { lazy, useState } from 'react';
import useSettings from './hooks/useSettings';
import useFileManager from './hooks/useFileManager';
import useContentMerger from './hooks/useContentMerger';
import Header from './pages/header.jsx';
import Footer from './pages/footer.jsx';
import FileUploadSection from './pages/home/fileUpload.section.jsx';
import NoLocationsSection from './pages/home/noLocations.section.jsx';

const Map = lazy(() => import('./components/Map'));

function App() {

  const [noLocations, setNoLocations] = useState(false);

  // Manage settings
  const [settings, handleSettingsChange] = useSettings({
    msgPosition: "closest"
  });

  // Manage files and data files
  const [handleFiles, handleDataFile, resetFileManager, dataFiles, files] = useFileManager();

  // Manage the map
  const [mapData, resetMerger] = useContentMerger({
    files: files,
    msgPosition: settings.msgPosition
  });

  // The user has uploaded a new file
  const handleNewUploadClick = () => {
    resetFileManager()
    resetMerger();
    setNoLocations(false);
  }

  // Handle uploaded files error (ex: invalid chat export)
  const handleFilesError = () => {
    setNoLocations(true);
  }

  // There's data
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
