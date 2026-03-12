import { FormattedMessage } from 'react-intl';

import SlButton from '@shoelace-style/shoelace/dist/react/button/index.js';
import SlIcon from '@shoelace-style/shoelace/dist/react/icon/index.js';

export default function SaveButton({
  data, onClick,
}) {
  function handleClick() {
    onClick(data);
  }

  return (
    <SlButton variant="default" outline size="small" onClick={handleClick}>
      <SlIcon slot="prefix" name="cloud-arrow-up-fill"></SlIcon>
      <FormattedMessage id="app.map.save" defaultMessage="Save" />
    </SlButton>
  );
}
