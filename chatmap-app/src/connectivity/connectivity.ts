import * as Network from 'expo-network';
import {useSyncExternalStore} from 'react';
import {AppState} from 'react-native';

import {HEALTH} from '../config';
import {checkHealth} from './health';
import {ConnectivityMonitor, type ConnectivityState} from './monitor';

export const connectivity = new ConnectivityMonitor(checkHealth, HEALTH);

export function useConnectivity(): ConnectivityState {
    return useSyncExternalStore(connectivity.subscribe, connectivity.getState);
}

export function startConnectivity(): () => void {
    const appState = AppState.addEventListener('change', (next) => {
        if (next === 'active') {
            connectivity.start();
        } else {
            connectivity.stop();
        }
    });
    const network = Network.addNetworkStateListener(() => connectivity.networkChanged());

    if (AppState.currentState === 'active') {
        connectivity.start();
    }

    return () => {
        appState.remove();
        network.remove();
        connectivity.stop();
    };
}
