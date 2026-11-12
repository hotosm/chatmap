import { FormattedMessage } from "react-intl";

import SlButton from '@shoelace-style/shoelace/dist/react/button/index.js';
import SlIcon from "@shoelace-style/shoelace/dist/react/icon/index.js";

import { useConfigContext } from "../../context/ConfigContext.jsx";
import { usesKeys } from "../Tags";
import { groupMessagesOn, messagesOn, pageOf } from "./messages.js";

// The way from a map to the messages of its groups, for its owner. Nothing for a map read without its keys
export default function MessagesLink({ mapData, data }) {
    const { config } = useConfigContext();
    if (!groupMessagesOn(config) || !messagesOn(mapData, usesKeys(data))) return null;

    return (
        <SlButton className="messagesLink" size="small" href={pageOf(`/map/${mapData.id}/messages`)}>
            <SlIcon name="chat-square-text" slot="prefix" />
            <FormattedMessage id="app.messages.title" defaultMessage="Messages" />
        </SlButton>
    );
}
