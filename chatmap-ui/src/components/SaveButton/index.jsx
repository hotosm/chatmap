import { useCallback } from 'react';
import { FormattedMessage } from 'react-intl';

import { useConfigContext } from '../../context/ConfigContext';

import SlButton from '@shoelace-style/shoelace/dist/react/button/index.js';
import SlIcon from '@shoelace-style/shoelace/dist/react/icon/index.js';

import { useAuth } from '../../context/AuthContext';

export default function SaveButton({data}) {
  const { isAuthenticated } = useAuth();
  const { config } = useConfigContext();

  const saveMap = useCallback(async () => {
    await fetch(`${config.API_URL}/map`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
  }, []);

  function handleSave() {
    if (isAuthenticated) {
      saveMap(data);
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
