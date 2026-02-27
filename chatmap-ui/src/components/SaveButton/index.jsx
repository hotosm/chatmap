import { FormattedMessage } from 'react-intl';

import SlButton from '@shoelace-style/shoelace/dist/react/button/index.js';
import SlIcon from '@shoelace-style/shoelace/dist/react/icon/index.js';

import useApi from '../ChatMap/useApi';
import { useAuth } from '../../context/AuthContext';

export default function SaveButton() {
  const { saveMap } = useApi();
  const { isAuthenticated } = useAuth();

  function handleSave() {
    if (isAuthenticated) {
      saveMap({yes: "no"});
    } else {
      console.log("not authenticated");
    }
  }

  return (
    <SlButton variant="default" outline size="small" onClick={handleSave}>
      <SlIcon slot="prefix" name="cloud-arrow-up-fill"></SlIcon>
      <FormattedMessage id="app.map.save" defaultMessage="Save" />
    </SlButton>
  );
}
