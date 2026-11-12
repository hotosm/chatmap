import { useEffect, useRef, useState } from "react";
import { FormattedMessage, useIntl } from "react-intl";
import { Marker } from "maplibre-gl";

import SlDialog from "@shoelace-style/shoelace/dist/react/dialog/index.js";
import SlInput from "@shoelace-style/shoelace/dist/react/input/index.js";
import SlButton from '@shoelace-style/shoelace/dist/react/button/index.js';
import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";
import SlSelect from "@shoelace-style/shoelace/dist/react/select/index.js";
import SlOption from "@shoelace-style/shoelace/dist/react/option/index.js";

import useTagsApi from "./useTagsApi.js";
import { newPoint, selectable } from "./tags.js";

// Adds a point to the map by hand: a click on the map tells where it is,
// then it takes a name and, if wanted, a value of the key that colors the map.
export default function AddPoint({ map, mapId, colorKey, adding, show, onAdd }) {
  const intl = useIntl();
  const { createPoint, setPointTag } = useTagsApi();

  // Where the new point goes: null, "picking" while waiting for the click, or its coordinates
  const [place, setPlace] = useState(null);
  const [name, setName] = useState("");
  const [valueId, setValueId] = useState(null);
  const [error, setError] = useState(null);
  // The point was added, but not its value of this key; the notice goes away after a while
  const [withoutValue, setWithoutValue] = useState(null);
  useEffect(() => {
    if (!withoutValue) return;
    const timer = setTimeout(() => setWithoutValue(null), 10000);
    return () => clearTimeout(timer);
  }, [withoutValue]);
  const [loading, setLoading] = useState(false);
  const marker = useRef(null);

  const options = selectable(colorKey);
  const selected = options.find((item) => item.id === valueId);

  const picking = place === "picking";
  const placed = Array.isArray(place);

  useEffect(() => {
    if (!map.current) return;

    // The points of the map do not open while a new one is being added
    adding.current = place !== null;
    map.current.getContainer().classList.toggle("map--picking", picking);

    if (marker.current) {
      marker.current.remove();
      marker.current = null;
    }
    if (placed) {
      const element = document.createElement("div");
      element.className = "addPoint__marker";
      marker.current = new Marker({ element }).setLngLat(place).addTo(map.current);
    }

    if (!picking) return;
    // Escape gives up placing the point
    const cancel = (event) => event.key === "Escape" && setPlace(null);
    window.addEventListener("keydown", cancel);
    const pick = (event) => {
      setName("");
      setValueId(null);
      setError(null);
      setPlace([event.lngLat.lng, event.lngLat.lat]);
    };
    map.current.once("click", pick);
    return () => {
      map.current.off("click", pick);
      window.removeEventListener("keydown", cancel);
    };
  }, [place]);

  // The marker goes away with the map
  useEffect(() => () => marker.current && marker.current.remove(), []);

  if (!show || !mapId) return null;

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;

    const { request, feature } = newPoint({
      id: crypto.randomUUID(),
      name: trimmed,
      coordinates: place,
      time: new Date().toISOString(),
    });

    setLoading(true);
    const created = await createPoint(mapId, request);
    // The point is already on the map when its value cannot be saved
    const saved = created && valueId ?
      await setPointTag(request.id, colorKey.id, { action: "set", value_id: valueId }) : null;
    setLoading(false);

    if (!created) {
      setError(intl.formatMessage({
        id: "app.tags.addPoint.error",
        defaultMessage: "The point could not be added."
      }));
      return;
    }
    if (saved) {
      feature.properties.point_tags = saved.tags;
    }
    setWithoutValue(valueId && !saved ? colorKey.key : null);
    setPlace(null);
    onAdd(feature);
  }

  return (
    <div className="addPoint">
      { picking ?
        <span className="addPoint__hint">
          <SlIcon name="crosshair" />
          <FormattedMessage id="app.tags.addPoint.pick" defaultMessage="Click on the map to place the point" />
          <button type="button" className="addPoint__cancel" onClick={() => setPlace(null)}>
            <FormattedMessage id="app.dialog.confirm.cancel" defaultMessage="Cancel" />
          </button>
        </span>
      :
        <SlButton pill onClick={() => { setWithoutValue(null); setPlace("picking"); }}>
          <SlIcon name="plus-lg" slot="prefix" />
          <FormattedMessage id="app.tags.addPoint" defaultMessage="Add point" />
        </SlButton>
      }
      { withoutValue &&
        <span className="addPoint__warning" role="status">
          <FormattedMessage
            id="app.tags.addPoint.withoutValue"
            defaultMessage="The point was added without {key}. Give it from its popup."
            values={{ key: withoutValue }}
          />
        </span>
      }

      <SlDialog
        className="tags__dialog"
        open={placed}
        onSlRequestClose={(event) => loading && event.preventDefault()}
        onSlAfterHide={(event) => event.target === event.currentTarget && setPlace(null)}
      >
        <h2 slot="label" className="dialog__title">
          <FormattedMessage id="app.tags.addPoint" defaultMessage="Add point" />
        </h2>

        { error &&
          <div className="error error-box">
            { error }
          </div>
        }

        {/* Typing here does not move the map to another point */}
        <form onSubmit={handleSubmit} onKeyDown={(event) => event.stopPropagation()}>
          <SlInput
            className="tags__input"
            required
            value={name}
            label={intl.formatMessage({ id: "app.tags.addPoint.nameLabel", defaultMessage: "Name" })}
            placeholder={intl.formatMessage({ id: "app.tags.addPoint.name", defaultMessage: "Ex: South access" })}
            onSlInput={(event) => setName(event.target.value)}
          />

          { colorKey && options.length > 0 &&
            <SlSelect
              className="tags__input"
              hoist
              clearable
              value={valueId || ""}
              label={colorKey.key}
              placeholder={intl.formatMessage({ id: "app.tags.none", defaultMessage: "Not chosen" })}
              onSlChange={(event) => setValueId(event.target.value || null)}
            >
              { selected &&
                <span slot="prefix" className="tags__dot" style={{ backgroundColor: selected.color || undefined }} />
              }
              { options.map((item) =>
                <SlOption value={item.id} key={item.id}>
                  <span slot="prefix" className="tags__dot" style={{ backgroundColor: item.color || undefined }} />
                  {item.value}
                </SlOption>
              )}
            </SlSelect>
          }

          <div className="tags__buttons">
            <SlButton disabled={loading} onClick={() => setPlace(null)}>
              <FormattedMessage id="app.dialog.confirm.cancel" defaultMessage="Cancel" />
            </SlButton>
            <SlButton type="submit" variant="primary" className="dark-btn" loading={loading}>
              <FormattedMessage id="app.dialog.confirm.ok" defaultMessage="Ok" />
            </SlButton>
          </div>
        </form>
      </SlDialog>
    </div>
  );
};
