import { useEffect } from "react";
import maplibregl from "maplibre-gl";
import { renderToString } from "react-dom/server";

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
      popupRef.current = new maplibregl.Popup({
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
