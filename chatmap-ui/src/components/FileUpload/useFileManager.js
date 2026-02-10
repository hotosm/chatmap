import { useState } from 'react';

/**
 * Strips path from a filename
 * ex: myfilename.txt instead of /files/myfilename.txt
 * @param {string} filename
 * @returns {string} filename without path
 */
function stripPath(filename) {
    return filename.substring(filename.lastIndexOf("/") + 1, filename.length);
}

/**
 * Hook for managing files
 *
 *  It will keep the states for files and dataFiles
 *  files: a dictionary of files, key is 'filename' ex: files[filename]
 *  dataFiles: data files (ex: images, videos) as a dictionary
 */
function useFileManager() {

    const [dataFiles, setDataFiles] = useState();
    const [files, setFiles] = useState(null);

    // Files handler
    const handleFiles = (files) => {
        setFiles(files)
    }

    // Data files (ex: images, videos) handler
    const handleDataFile = (filename, fileContent) => {
        setDataFiles(prevState => (
            {...prevState, ...{[stripPath(filename)]: fileContent}}
        ));
    }

    // Reset the handler, clear files and data files
    const resetFileManager = () => {
        setFiles(null);
        setDataFiles();
    }

    return [handleFiles, handleDataFile, resetFileManager, dataFiles, files];

}

export default useFileManager;
