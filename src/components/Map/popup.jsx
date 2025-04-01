import { useEffect } from "react";
import { Popup as PopupGL } from "maplibre-gl";
import { renderToString } from "react-dom/server";

// It manages popups, creating  maplibregl.Popup objects when necessary.
export default function Popup({
  latitude,
  longitude,
  children,
  closeOnMove,
  closeButton,
  closeOnClick,
  popupRef
}) {
  useEffect(() => {
    if (!popupRef.current) {
      popupRef.current = new PopupGL({
        closeOnClick: false,
        closeOnMove,
        closeButton,
        className: "popup",
      });
    }
    popupRef.current
      .setLngLat([longitude, latitude])
      .setHTML(renderToString(children));
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
