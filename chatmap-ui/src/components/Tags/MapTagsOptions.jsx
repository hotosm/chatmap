import { useState } from "react";
import { createPortal } from "react-dom";
import { FormattedMessage } from "react-intl";

import SlButton from '@shoelace-style/shoelace/dist/react/button/index.js';
import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";

import MapTagsDialog from "./MapTagsDialog.jsx";
import { freeTagsInUse, usesKeys, valuesInUse } from "./tags.js";

// The entry of the tags of a map in its options, for its owner. Nothing for a map read without its keys
export default function MapTagsOptions({ mapData, data, onChange }) {
  const [dialogOpen, setDialogOpen] = useState(false);

  if (!usesKeys(data) || !mapData.owner || !mapData.id) return null;

  return (
    <div className="map__options_live">
      <h3><FormattedMessage id="app.tags.title" defaultMessage="Tags" /></h3>
      <SlButton className="map__options_button" size="small" onClick={() => setDialogOpen(true)}>
        <SlIcon name="tags" slot="prefix" />
        <FormattedMessage id="app.tags.setUp" defaultMessage="Set up tags" />
      </SlButton>

      {/* Outside of the options menu, so it stays open when the menu closes */}
      { createPortal(
        <MapTagsDialog
          open={dialogOpen}
          setOpen={setDialogOpen}
          mapId={mapData.id}
          keys={data.keys || []}
          inUse={valuesInUse(data.features)}
          freeTagsInUse={freeTagsInUse(data.features)}
          onChange={onChange}
        />,
        document.body
      )}
    </div>
  );
}
