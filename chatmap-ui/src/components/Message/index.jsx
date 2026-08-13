import { formatDate, GetMessage } from "../Map/utils";

export default function Message({
  message,
  msgType,
  selected,
  ref,
  dataFiles,
  onRemove,
  showMessageOptions,
  coordinates
}) {

  const onCoordsClick = () => {
    const coords = getShortCoords();
    navigator.clipboard.writeText(`${coords[1]},${coords[0]}`)
  }

  const getShortCoords = () => {
    return [
      Math.round(coordinates[1]  * 10000)/10000,
      Math.round(coordinates[0]  * 10000)/10000
    ]
  }

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
        <sl-icon-button
          className="copyIcon"
          name="copy"
          label="Copy"
          onClick={onCoordsClick}
        ></sl-icon-button>
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
