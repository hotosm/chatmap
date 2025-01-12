import { useState } from 'react';

function stripPath(filename) {
    return filename.substring(filename.lastIndexOf("/") + 1, filename.length);
}

function useFileManager() {

    const [dataFiles, setDataFiles] = useState();
    const [files, setFiles] = useState();

    const handleFiles = (files) => {
        setFiles(files)
    }
    const handleDataFile = (filename, fileContent) => {
        setDataFiles(prevState => (
            {...prevState, ...{[stripPath(filename)]: fileContent}}
        ));
    }

    const resetFileManager = () => {
        setFiles(null);
        setDataFiles();
    }

    return [handleFiles, handleDataFile, resetFileManager, dataFiles, files];

}

export default useFileManager;
