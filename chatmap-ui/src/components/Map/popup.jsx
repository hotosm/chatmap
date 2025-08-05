import { useEffect, useRef } from "react";
import { Popup as PopupGL } from "maplibre-gl";
import { createRoot } from "react-dom/client";
import Tagger from '../Tagger';
import Message from '../Message';

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
        maxWidth: '300px',
        anchor: 'left',
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
        <Message
          message={feature.properties}
          dataFiles={dataFiles}
        />
        <Tagger
          tags={feature.properties.tags || []}
          onAddTag={tag => onAddTag(tag, feature)} 
          onRemoveTag={tag => onRemoveTag(tag, feature)} 
        />
      </div>
    </PopupGLWrapper>
  )
}
