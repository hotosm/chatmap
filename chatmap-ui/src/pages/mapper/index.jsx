import { openDB, deleteDB } from 'idb';
import { useState, useRef, useEffect } from "react";
import { FormattedMessage, FormattedRelativeTime } from "react-intl";
import Header from "../header.jsx";
import { useAuth } from '../../context/AuthContext.jsx';
import SlInput from "@shoelace-style/shoelace/dist/react/input/index.js";
import SlButton from "@shoelace-style/shoelace/dist/react/button/index.js";
import SlIconButton from '@shoelace-style/shoelace/dist/react/icon-button/index.js';
import SlIcon from '@shoelace-style/shoelace/dist/react/icon/index.js';
import DownloadButton from '../../components/DownloadButton';
import ConfirmDialog from "../../components/ConfirmDialog/index.jsx";

import '../../styles/mapper.css';

const dbName = 'ChatMapDB';
const storeName = 'chatmapData';

async function getDB() {
  return openDB(dbName, 1, {
    upgrade(db) {
      if (!db.objectStoreNames.contains(storeName)) {
        db.createObjectStore(storeName);
      }
    },
  });
}

async function removeDataFiles(dataFilesIndex) {
  const db = await getDB();
  for (let i = 0; i < dataFilesIndex; i++) {
    await db.delete(storeName, `${i+1}.jpg`);
  }
}

async function saveToIndexedDB(key, value) {
  if (value === undefined || value === null) return;
  const db = await getDB();
  await db.put(storeName, value, key);
}

async function loadFromIndexedDB(key) {
  const db = await getDB();
  return db.get(storeName, key);
}

const getTileURL = (lon, lat) => {
 const zoom = 18;
 const latTile = Math.floor((1-Math.log(Math.tan(lat*Math.PI/180) + 1/Math.cos(lat*Math.PI/180))/Math.PI)/2 *Math.pow(2,zoom));
 const lonTile = Math.floor((lon+180)/360*Math.pow(2,zoom));
 return `https://tile.openstreetmap.org/${zoom}/${lonTile}/${latTile}.png`;
}

const MessageMedia = ({ name }) => {
  const [src, setSrc] = useState(null);
  useEffect(() => {
    const loadImage = async () => {
      const image = await loadFromIndexedDB(name);
      setSrc(image);
    }
    loadImage();
  }, [name]);
  if (src) {
    return <img src={URL.createObjectURL(src)} />;
  }
  return null;
}

export default function Mapper() {
  const { isAuthenticated } = useAuth();
  const [locationShared, setLocationShared] = useState(false);
  const [messages, setMessages] = useState([]);
  const [data, setData] = useState({
    type: "FeatureCollection",
    _chatmapId: Date.now().toString(),
    features: []
  });
  const [dataFilesIndex, setDataFilesIndex] = useState(0);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [confirmDialogData, setConfirmDialogData] = useState();

  const initializedRef = useRef(false);
  const dbRef = useRef(null)

  // Load state from indexDB
  useEffect(() => {
    const loadState = async () => {
      try {
        const savedLocationShared = await loadFromIndexedDB('locationShared');
        const savedMessages = await loadFromIndexedDB('messages');
        const savedData = await loadFromIndexedDB('data');
        const savedDataFilesIndex = await loadFromIndexedDB('dataFilesIndex');

        if (savedDataFilesIndex) setDataFilesIndex(savedDataFilesIndex);
        if (savedData) setData(savedData);
        if (savedMessages) setMessages(savedMessages);
        if (savedLocationShared !== undefined) setLocationShared(savedLocationShared);

        initializedRef.current = true;
      } catch (err) {
        console.error('Failed to load from IndexedDB', err);
        initializedRef.current = true;
      }
    };

    loadState();
  }, []);

  // Save state to indexDB
  useEffect(() => {
    if (!initializedRef.current) return;
    const saveState = async () => {
      try {
        await saveToIndexedDB('locationShared', locationShared);
        await saveToIndexedDB('messages', messages);
        await saveToIndexedDB('data', data);
        await saveToIndexedDB('dataFilesIndex', dataFilesIndex);
      } catch (err) {
        console.error('Failed to save to IndexedDB', err);
      }
    }
    saveState();
  }, [locationShared, messages, data, dataFilesIndex]);

  const getDataFiles = async () => {
    const dataFiles = {};
    for (let i = 0; i < dataFilesIndex; i++) {
      const filename = `${i+1}.jpg`;
      dataFiles[filename] = await loadFromIndexedDB(filename);
    }
    return dataFiles;
  }

  const locationClickHandler = async () => {
    if (!navigator.geolocation) {
      console.error("Geolocation is not supported by your browser");
      return;
    }
    const position = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        resolve,
        reject, (e) => { console.log(e) },
        {
          enableHighAccuracy: true,
          timeout: 5000,
          maximumAge: 0
        }
      );

    });

    const { latitude, longitude } = position.coords;
    const featureIndex = data.features.length;
    setMessages([
      ...messages,
      {
        id: messages.length,
        dataIndex: featureIndex,
        type: "LOCATION"
      }
    ]);
    setData({
      ...data,
      features:
        [
            ...data.features,
            {
            "type": "Feature",
            "properties": {
              "time": new Date()
            },
            "geometry": {
              "type": "Point",
              "coordinates": [
                longitude,
                latitude
              ]
            }
          }
        ]
    });
    setLocationShared(true);
  }

  const cameraClickHandler = async () => {
    try {

      // Use a hidden file input element
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = 'image/*';
      input.capture = 'environment'; // Back camera
      input.style.display = 'none';
      document.body.appendChild(input);
      input.click();

      const filePromise = new Promise((resolve, reject) => {
        input.onchange = (event) => {
          const file = event.target.files[0];
          if (file) {
            resolve(file);
          }
        };

        // Cleanup after a delay to ensure the event fires
        setTimeout(() => {
          document.body.removeChild(input);
          if (!input.onchange) {
            reject(new Error('File input was cancelled'));
          }
        }, 5000);
      });

      // Get file
      const file = await filePromise;
      const blob = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(new Blob([reader.result], { type: file.type }));
        reader.onerror = reject;
        reader.readAsArrayBuffer(file);
      });

      const featureIndex = data.features.length - 1;

      setMessages([
        ...messages,
        {
          id: messages.length,
          dataIndex: dataFilesIndex + 1,
          type: "MEDIA"
        }
      ]);

      setData(prevData => {
        const newData = {...prevData};
        newData.features[featureIndex].properties.file = `${dataFilesIndex + 1}.jpg`;
        newData.features[featureIndex].properties.id = featureIndex;
        return newData;
      });

      await saveToIndexedDB(`${dataFilesIndex + 1}.jpg`, blob);

      setDataFilesIndex(prevIndex => (
        dataFilesIndex + 1
      ));

      setLocationShared(false);

    } catch (error) {
      console.log("Error getting the picture")
    }
  };

  const cleanChatHandler = async () => {
    await removeDataFiles(dataFilesIndex);
    setLocationShared(false);
    setMessages([]);
    setData({
      type: "FeatureCollection",
      _chatmapId: Date.now().toString(),
      features: []
    });
    setDataFilesIndex(0);
  }

  return (
    <div className="mapper">
        <Header pageTitle={isAuthenticated ? "My Maps" : "Maps"} noAuth>
          <DownloadButton
            className="mapper_exportButton"
            label="Export"
            variant="text"
            data={data}
            getDataFiles={getDataFiles}
          />
          <SlIconButton
            className="mapper_cleanChatButton"
            name="trash-fill"
            variant="text"
            caret
            onClick={() => setConfirmDialogOpen(true)}
          >
          </SlIconButton>
        </Header>
        <div className="mapper_container">
          <div className="mapper_messages">
            {
              messages.map((message) => (
                message.type === "LOCATION" ?
                <div className="mapper_message" key={message.id}>
                  <div className="mapper_messageLocation">
                      <div className="mapper_messageLocationIconWrapper">
                          <div className="mapper_messageLocationIcon"></div>
                      </div>
                      <img src={getTileURL(
                          data.features[message.dataIndex].geometry.coordinates[0],
                          data.features[message.dataIndex].geometry.coordinates[1]
                        )} />
                  </div>
                </div>
                :
                <div key={message.id} className="mapper_message">
                  <div className="mapper_messageMedia">
                    <MessageMedia name={`${message.dataIndex}.jpg`} />
                  </div>
                </div>
              ))
            }
          </div>
          <div className="mapper_messageInputWrapper">
            <SlIconButton
              slot="trigger"
              name="chat-heart"
              caret
              onClick={locationClickHandler}
              disabled={locationShared}
            >
            </SlIconButton>
            <div className="mapper_messageInput">
              <SlInput
                name="message"
                disabled
                placeholder="Share location, then picture. Repeat."
              />
            </div>
            <SlIconButton
              slot="trigger" 
              name="camera"
              caret
              onClick={cameraClickHandler}
              onTouchEndCapture={cameraClickHandler}
              disabled={!locationShared}
            >
            </SlIconButton>
          </div>
        </div>
        <ConfirmDialog
          open={confirmDialogOpen}
          setOpen={setConfirmDialogOpen}
          onConfirm={() => cleanChatHandler()}
          title={{id: "app.maps.areYouSure", defaultMessage: "Are you sure?"}}
        >
          All data will be removed.
        </ConfirmDialog>
    </div>
  );
};
