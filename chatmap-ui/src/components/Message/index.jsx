import { formatDate, getMessage } from "../Map/utils";

function Message({ message, msgType, selected, ref, dataFiles, onRemove }) {
        return (
            <div
                key={message.id}
                className={`message
                    ${selected ? 'selected' : ''}
                    ${message.removed ? 'removed' : ''}
                    ${message.mapped ? 'mapped' : ''}
                `}
                ref={ref}
            >
                <p className="userinfo">
                    <span className="msgUsername">{message.username.split("@")[0]}</span>
                    {/* <span className="msgDatetime">{formatDate(message.time)}</span> */}
                    <span className="msgDatetime">Index: {message.index}</span>
                    <sl-icon-button
                        className="removeIcon"
                        name="trash"
                        label="Remove"
                        onClick={onRemove}
                    ></sl-icon-button>
                    {message.removed ? <span className="removedLabel">(deleted)</span> : ""}
                </p>
                <div>{ getMessage(message, msgType, dataFiles) }</div>
            </div>
        )

}

export default Message;
