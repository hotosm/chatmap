import { formatDate, GetMessage } from "../Map/utils";

export default function Message({
  message, msgType, selected, ref, dataFiles, onRemove, showMessageOptions,
}) {
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
        { message.username && <span className="msgUsername">{message.username.split("@")[0]}</span> }
        <span className="msgDatetime">{formatDate(message.time)}</span>
        { showMessageOptions ?
        <sl-icon-button
          className="removeIcon"
          name="trash"
          label="Remove"
          onClick={onRemove}
        ></sl-icon-button>
        : ""}
        {message.removed ? <span className="removedLabel">(deleted)</span> : ""}
      </p>
      <div>
        <GetMessage message={message} msgType={msgType} dataFiles={dataFiles} />
      </div>
    </div>
  )
};
