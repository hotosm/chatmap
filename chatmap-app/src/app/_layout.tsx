import { Stack } from 'expo-router';
import { useEffect } from 'react';
import { Alert } from 'react-native';

import { startConnectivity } from '../connectivity/connectivity';
import { accessRemovedMessage, accessRemovedTitle } from '../contributor/accessRemovedNotice';
import { onMapsRemoved } from '../contributor/refreshMaps';
import { startSync } from '../sync';

export default function RootLayout() {
  useEffect(() => {
    const stopConnectivity = startConnectivity();
    const stopSync = startSync();
    const stopNotice = onMapsRemoved((removed) => Alert.alert(accessRemovedTitle(removed), accessRemovedMessage(removed)));

    return () => {
      stopNotice();
      stopSync();
      stopConnectivity();
    };
  }, []);

  return <Stack />;
}
