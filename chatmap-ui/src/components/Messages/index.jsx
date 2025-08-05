import {useRef, useEffect } from "react";
import Message from '../Message';

function Messages({ messages, selectedFeature, dataFiles }) {

    const messageRefs = useRef({});

    useEffect(() => {
        if (selectedFeature && messageRefs.current[selectedFeature.id]) {
            messageRefs.current[selectedFeature.id].scrollIntoView({
                behavior: 'smooth',
                block: 'start',
            });
        }
    }, [selectedFeature, messages]);

    return (
    <div className="messages">
        {
            Object.keys(messages).map(key => (
                <Message
                    key={key}
                    dataFiles={dataFiles}
                    message={messages[key]}
                    selected={
                        parseInt(selectedFeature?.id) === parseInt(key) ||
                        parseInt(key) === parseInt(selectedFeature?.related)
                    }
                    ref={el => messageRefs.current[key] = el}
                />
            ))
        }
    </div>
    );
}

export default Messages;
