import React from "react";
import CardOption from "./CardOption";
import { FormattedMessage } from 'react-intl';

function Settings({ settings, onChange }) {

  const handleOptionClick = (name) => {
    onChange({
      ...settings,
      msgPosition: name
    })
  }

  return (
    <div className="">
      <div className="cardOptions">
        <CardOption 
          selected={settings.msgPosition === "closest"} 
          img={"img/config-closest.png"} 
          name="closest"
          title={<FormattedMessage
            id = "app.config.closestMsg"
            defaultMessage="closest"
          />}
          onClick={handleOptionClick}
        >
          <FormattedMessage
              id = "app.config.msgPositionTextStart"
              defaultMessage="It will search for locations and the"
            /> <strong> <FormattedMessage
                id = "app.config.closestMsg"
                defaultMessage="closest"
              /> </strong> <FormattedMessage
              id = "app.config.msgPositionTextEnd"
              defaultMessage="message from the same user."
            />
        </CardOption>

        <CardOption
          selected={settings.msgPosition === "after"}
          img={"img/config-after.png"}
          name="after"
          title={<FormattedMessage
            id = "app.config.closestNextMsg"
            defaultMessage="next"
          />}
          onClick={handleOptionClick}
        >
          <FormattedMessage
              id = "app.config.msgPositionTextStart"
              defaultMessage="It will search for locations and the"
            /> <strong>
              <FormattedMessage
                id = "app.config.closestNextMsg"
                defaultMessage="next"
              />
              </strong> <FormattedMessage
              id = "app.config.msgPositionTextEnd"
              defaultMessage="message from the same user."
            />
        </CardOption>

        <CardOption
          selected={settings.msgPosition === "before"}
          img={"img/config-before.png"}
          name="before"
          title={<FormattedMessage
            id = "app.config.closestPreviousMsg"
            defaultMessage="previous"
          />}
          onClick={handleOptionClick}
        >
            <FormattedMessage
              id = "app.config.msgPositionTextStart"
              defaultMessage="It will search for locations and the"
            /> <strong>
              <FormattedMessage
                id = "app.config.previousNextMsg"
                defaultMessage="next"
              />
            </strong> <FormattedMessage
              id = "app.config.msgPositionTextEnd"
              defaultMessage="message from the same user."
            />
        </CardOption>
      </div>
    </div>

  );
}

export default Settings;
