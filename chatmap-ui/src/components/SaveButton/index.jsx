import { FormattedMessage } from 'react-intl';

import SlButton from '@shoelace-style/shoelace/dist/react/button/index.js';
import SlIcon from '@shoelace-style/shoelace/dist/react/icon/index.js';

import { useAuth } from '../../context/AuthContext';

export default function SaveButton({data, onClick}) {
  const { isAuthenticated } = useAuth();

  function handleClick() {
    if (isAuthenticated) {
      onClick(data);
    } else {
      console.log("not authenticated");
    }
  }

  return (
    <SlButton variant="default" outline size="small" onClick={handleClick}>
      <SlIcon slot="prefix" name="cloud-arrow-up-fill"></SlIcon>
      <FormattedMessage id="app.map.save" defaultMessage="Save" />
    </SlButton>
  );
}
