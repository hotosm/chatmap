import { useState, useCallback } from "react";
import { useConfigContext } from '../../context/ConfigContext.jsx'

/**
 *  ChatMap API
 *
 * @param {object} params - Parameters
 */
const useApi = (params = {}) => {
    const { config } = useConfigContext();

    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [mapData, setMapData] = useState({
        type: "FeatureCollection",
        features: []
    });
    const [QRImgSrc, setQRImgSrc] = useState();
    const [status, setStatus] = useState();
    const [mapShare, setMapShare] = useState({});

    /**
     * Common pattern for all requests
     */
    async function wrapper(callback) {
      setIsLoading(true);
      setError(null);
      try {
        await callback();
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    }

    // Logout session
    const logoutSession = useCallback(async () => {
      await wrapper(async () => {
            const response = await fetch(`${config.API_URL}/logout`, {
                method: 'GET',
                credentials: 'include',
            });
            if (!response.ok) throw new Error('Failed to logout');
      });
    });

    // Fetch map data related to a session
    const fetchMapData = useCallback(async (id) => {
        const url = id ? `${config.API_URL}/map/${id}` : `${config.API_URL}/map/new`;
        await wrapper(async () => {
            const response = await fetch(url, {
                method: 'GET',
                credentials: 'include',
            });
            if (response.status === 401) {
                console.log("Not authorized")
            }
            if (!response.ok) throw new Error('Failed to fetch data');
            const result = await response.json();
            setMapData(result);
        });
    }, [params]);

    // Fetch a new QR code for linking a device
    const fetchQRCode = useCallback(async () => {
      await wrapper(async () => {
            const response = await fetch(`${config.API_URL}/qr`, {
                method: 'GET',
                credentials: 'include',
            });
            if (!response.ok) throw new Error('Failed to fetch QR code');
            const blob = await response.blob();
            const objectURL = URL.createObjectURL(blob);
            setQRImgSrc(objectURL);
      });
    }, []);

    // Fetch status of linking a device
    const fetchStatus = useCallback(async () => {
      await wrapper(async () => {
            const response = await fetch(`${config.API_URL}/status`, {
                method: 'GET',
                credentials: 'include',
            });
            if (!response.ok) {
                throw new Error('Failed to fetch status');
            }
            const result = await response.json();
            setStatus(result.status);
      });
    }, []);

    // Fetch a sharing code for accessing the map
    const updateMapShare = useCallback(async (id) => {
      await wrapper(async () => {
            const response = await fetch(`${config.API_URL}/map/${id}/share/`, {
                method: 'PUT',
                credentials: 'include',
            });
            if (!response.ok) {
                throw new Error('Failed to fetch share');
            }
            const result = await response.json();
            setMapShare(result);
      });
    }, []);

    // Update the removed property of a point
    const removePoint = useCallback(async (id) => {
      await wrapper(async () => {
            const response = await fetch(`${config.API_URL}/point/${id}/remove/`, {
                method: 'PUT',
                credentials: 'include',
            });
            if (!response.ok) {
                throw new Error('Failed to fetch removed');
            }
            await response.json();
      });
    }, []);

    return {
        mapData,
        QRImgSrc,
        status,
        isLoading,
        error,
        fetchMapData,
        logoutSession,
        fetchQRCode,
        fetchStatus,
        updateMapShare,
        removePoint,
        mapShare,
    };
};

export default useApi;
