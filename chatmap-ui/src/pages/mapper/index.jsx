import { useState, useRef, useEffect } from "react";
import { FormattedMessage, FormattedRelativeTime } from "react-intl";
import Header from "../header.jsx";
import { useAuth } from '../../context/AuthContext.jsx';
import SlInput from "@shoelace-style/shoelace/dist/react/input/index.js";
import SlButton from "@shoelace-style/shoelace/dist/react/button/index.js";
import SlIconButton from '@shoelace-style/shoelace/dist/react/icon-button/index.js';
import SlIcon from '@shoelace-style/shoelace/dist/react/icon/index.js';
import DownloadButton from '../../components/DownloadButton';

import '../../styles/mapper.css';

const getTileURL = (lon, lat) => {
 const zoom = 18;
 const latTile = Math.floor((1-Math.log(Math.tan(lat*Math.PI/180) + 1/Math.cos(lat*Math.PI/180))/Math.PI)/2 *Math.pow(2,zoom));
 const lonTile = Math.floor((lon+180)/360*Math.pow(2,zoom));
 return `https://tile.openstreetmap.org/${zoom}/${lonTile}/${latTile}.png`;
}

export default function Mapper() {
  const { isAuthenticated } = useAuth();
  const [locationShared, setLocationShared] = useState(false);
  const [messages, setMessages] = useState([]);
  const messagesContainerRef = useRef();
  const [data, setData] = useState({
    type: "FeatureCollection", 
    _chatmapId: Date.now().toString(),
    features: []
  });
  const [dataFiles, setDataFiles] = useState({});

  const scrollToBottom = () => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  };

  // Effect to scroll when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages])

  const locationClickHandler = async () => {
    if (!navigator.geolocation) {
      console.error("Geolocation is not supported by your browser");
      return;
    }
    const position = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        () => { setLocationShared(true); },
        (e) => { console.log(e) },
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

      const dataFilesIndex = Object.keys(dataFiles).length;
      const featureIndex = data.features.length - 1;

      setMessages([
        ...messages,
        {
          id: messages.length,
          dataIndex: dataFilesIndex,
          type: "MEDIA"
        }
      ]);

      setData(prevData => {
        const newData = {...prevData};
        newData.features[featureIndex].properties.file = `${dataFilesIndex}.jpg`;
        newData.features[featureIndex].properties.id = featureIndex;
        return newData;
      });

      setDataFiles(dataFiles => ({
        ...dataFiles,
        [`${dataFilesIndex}.jpg`]: blob
      }));

      setLocationShared(false);

    } catch (error) {
      console.log("Error getting the picture")
    }
  };

  return (
    <div className="mapper">
        <Header pageTitle={isAuthenticated ? "My Maps" : "Maps"} noAuth>
          <DownloadButton
            className="mapper_exportButton"
            label="Export"
            variant="text"
            data={data}
            dataFiles={dataFiles}
          />
        </Header>
        <div className="mapper_container">
          <div className="mapper_messages" ref={messagesContainerRef}>
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
                    <img src={URL.createObjectURL(dataFiles[`${message.dataIndex}.jpg`])} />
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
    </div>
  );
};
