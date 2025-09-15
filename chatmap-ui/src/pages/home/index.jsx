import { lazy, useState, useEffect } from 'react';
import useFileManager from '../../components/FileUpload/useFileManager.js';
import useContentMerger from '../../components/ChatMap/useContentMerger.js';
import Header from '../header.jsx';
import Footer from '../footer.jsx';
import FileUploadSection from './fileUpload.section.jsx';
import NoLocationsSection from './noLocations.section.jsx';
import { useMapDataContext } from '../../context/MapDataContext.jsx';

const Map = lazy(() => import('../../components/Map/index.jsx'));

function App() {

  const [noLocations, setNoLocations] = useState(false);
  const [selectedFeature, setSelectedFeature] = useState();
<<<<<<< HEAD
=======
  const [mediaOnly, setMediaOnly] = useState(true);
>>>>>>> origin/develop-merge

  // File Manager: Manages files and data files.
  // - handleFiles: handle all chat files
  // - handleDataFile: handle all other files (images, videos)
  // - resetFileManager: clear files and data files states
  // - dataFiles: stores all other files (images, videos)
  // - files: stores all chat files
  const [handleFiles, handleDataFile, resetFileManager, dataFiles, files] = useFileManager();

  // Content Merger: Handle chat content
  // - mapData: ready to use GeoJSON data created from chats
  // - resetMerger: clean everthing to upload a new file
  const [mapData, resetMerger] = useContentMerger({
<<<<<<< HEAD
    files: files
=======
    files: files,
    options: { mediaOnly }
>>>>>>> origin/develop-merge
  });
  

  useEffect(() => {
      // Public event for external integratons
      if (mapData.features.length > 0) {
        window._CHATMAP?.mapData && window._CHATMAP.mapData();
      }
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

  // Handle uploaded files error (ex: invalid chat export)
  const handleFilesError = () => {
    setNoLocations(true);
  }

  // Handle media only switch
  const handleMediaOnlyChange = () => {
    setMediaOnly(prevState => !prevState);
  }

  // There's data for the map!
  const dataAvailable = files && data && data.features && data.features.length > 0;

  const handleFeatureSelect = (feature) => {
    setSelectedFeature(feature.properties);
  }

  return (
    <>
    <div className="app">

        <Header
          dataAvailable={dataAvailable}
          dataFiles={dataFiles}
          mapData={data}
          handleNewUploadClick={handleNewUploadClick}
          showUploadButton={true}
        />

        {/* If there're no files, show file upload options */}
        { !files &&
          <div className="indexMain">
            <FileUploadSection
              mediaOnly={mediaOnly}
              handleFiles={handleFiles}
              handleDataFile={handleDataFile}
              handleMediaOnlyChange={handleMediaOnlyChange}
              onError={handleFilesError}
            />
            <Footer />
          </div>
        }

        {/* Thered's data, show the map! */}
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
    <div className="infoLinks">
        <div className="copy">
            <a href="https://github.com/hotosm/chatmap">This is free software</a>
        </div>
        <a href="https://www.hotosm.org/privacy">- We collect zero personal data. hotosm.org/privacy -</a>
        &nbsp;
<<<<<<< HEAD
        <a href="https://github.com/hotosm/chatmap">v0.4.12</a>
=======
        <a href="https://github.com/hotosm/chatmap">v0.4.13</a>
>>>>>>> origin/develop-merge
    </div>
    </>
  );
}

export default App;
