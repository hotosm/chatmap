import { formatDate, getMessage } from "../Map/utils";

function Message({ message, selected, ref, dataFiles }) {
        return (
            <div
                key={message.id}
                className={`message
                    ${selected ? 'selected' : ''}
                    ${message.mapped ? 'mapped' : ''}
                `}
                ref={ref}
            >
                <p className="userinfo">
                    <span className="msgUsername">{message.username.split("@")[0]}</span>
                    <span className="msgDatetime">{formatDate(message.time)}</span>
                </p>
                <div>{ getMessage(message, dataFiles) }</div>
            </div>
        )

}

export default Message;
