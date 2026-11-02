import { useEffect } from "react";
import { useParams } from 'react-router';
import { FormattedMessage } from "react-intl";

import SlButton from "@shoelace-style/shoelace/dist/react/button/index.js";
import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";

import Header from "../header.jsx";
import useAPI from '../../components/ChatMap/useApi.js';
import { usesKeys } from '../../components/Tags';
import { MessagesInbox, messagesOn, pageOf } from '../../components/Messages';

// The messages of the groups of a map, for its owner
export default function MessagesPage() {
  const { id } = useParams();
  const { fetchMapData, mapData } = useAPI();

  useEffect(() => {
    fetchMapData(id);
  }, [id]);

  const shown = messagesOn(mapData, usesKeys(mapData));

  return (
    <div className="app messages-view">
      <Header title={mapData.name} pageTitle={mapData.name}>
        <SlButton size="small" href={pageOf(`/map/${id}`)}>
          <SlIcon name="arrow-left" slot="prefix" />
          <FormattedMessage id="app.messages.backToMap" defaultMessage="Back to the map" />
        </SlButton>
      </Header>
      { shown && <MessagesInbox mapId={id} live={mapData.is_live} /> }
    </div>
  );
}
