import { useEffect, useRef } from "react";
import { Popup as PopupGL } from "maplibre-gl";
import { createRoot } from "react-dom/client";
import { formatDate, getMessage } from "./utils";
import Tagger from '../Tagger';

// It manages popups, creating  maplibregl.Popup objects when necessary.
const PopupGLWrapper = ({
  latitude,
  longitude,
  children,
  closeOnMove,
  closeButton,
  closeOnClick,
  popupRef,
}) => {

  const containerRef = useRef(document.createElement("div"));
  const rootRef = useRef(null); // Store the React root instance

  useEffect(() => {
    if (!popupRef.current) {
      popupRef.current = new PopupGL({
        closeOnClick: false,
        closeOnMove,
        closeButton,
        className: "popup",
      });
    }
    popupRef.current.setLngLat([longitude, latitude]);
    if (!rootRef.current) {
      rootRef.current = createRoot(containerRef.current);
    }
    rootRef.current.render(children);
    popupRef.current.setDOMContent(containerRef.current);
  }, [
    latitude,
    longitude,
    children,
    closeOnClick,
    closeOnMove,
    closeButton,
    popupRef,
  ]);

  return null;
}

export default function Popup ({
  feature,
  popupRef,
  dataFiles,
  onAddTag,
  onRemoveTag
}) {
  
  return (
    <PopupGLWrapper
      longitude={feature.geometry.coordinates[0]}
      latitude={feature.geometry.coordinates[1]}
      popupRef={popupRef}
      closeOnMove={false}
      closeButton={true}
      >
      <div className="activePopupFeatureContent">
        <p className="userinfo">
          <span className="msgUsername">{feature.properties.username}</span>
          <span className="msgDatetime">{formatDate(feature.properties)}</span>
        </p>
        <p className="message">
          { getMessage(feature.properties, dataFiles) }
        </p>
        <Tagger
          tags={feature.properties.tags || {}}
          onAddTag={(tag_key, tag_value) => onAddTag(tag_key, tag_value, feature)} 
          onRemoveTag={(tag_key, tag_value) => onRemoveTag(tag_key, feature)} 
        />
      </div>
    </PopupGLWrapper>
  )
}
