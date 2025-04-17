import React from "react";
import { formatDate, getMessage } from "../Map/utils";

function Message({ message, selected, ref, dataFiles }) {
        return (
            <div
                key={message.id}
                className={`message
                    ${selected && 'selected'}
                    ${message.mapped && 'mapped'}
                `}
                ref={ref}
            >
                <p className="userinfo">
                    <span className="msgUsername">{message.username}</span>
                    <span className="msgDatetime">{formatDate(message.time)}</span>
                </p>
                <p>{ getMessage(message, dataFiles) }</p>
            </div>
        )

}

export default Message;
