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

    // Unlink device
    const unlinkDevice = useCallback(async () => {
      await wrapper(async () => {
            const response = await fetch(`${config.API_URL}/logout`, {
                method: 'GET',
                credentials: 'include',
            });
            if (!response.ok) throw new Error('Failed to logout');
      });
    });

    // Unlink a live map
    const unlinkMap = useCallback(async (id) => {
      await wrapper(async () => {
            const response = await fetch(`${config.API_URL}/map/${id}/unlink/`, {
                method: 'PUT',
                credentials: 'include',
            });
            if (!response.ok) {
                throw new Error('Failed to fetch is_live');
            }
            const result = await response.json();
            console.debug(result);
      });
    }, []);

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

    // Fetch the bot configuration of a map: whether it is enabled and every
    // message it is set up to send
    const fetchBotSetup = useCallback(async (id) => {
      let setup = null;
      await wrapper(async () => {
            const response = await fetch(`${config.API_URL}/map/${id}/bot/`, {
                method: 'GET',
                credentials: 'include',
            });
            if (!response.ok) {
                throw new Error('Failed to fetch the bot setup');
            }
            setup = await response.json();
      });
      return setup;
    }, []);

    // Save the whole bot configuration in one request. The API rejects
    // enabling the bot while a required message is missing.
    const updateBotSetup = useCallback(async (id, setup) => {
      let saved = null;
      await wrapper(async () => {
            const response = await fetch(`${config.API_URL}/map/${id}/bot/`, {
                method: 'PUT',
                body: JSON.stringify(setup),
                headers: {"Content-Type": "application/json"},
                credentials: 'include',
            });
            if (!response.ok) {
                throw new Error('Failed to save the bot setup');
            }
            saved = await response.json();
      });
      return saved;
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

    // Update the tags property of a point
    const updatePointTags = useCallback(async (id, tags) => {
      await wrapper(async () => {
            const response = await fetch(`${config.API_URL}/point/${id}/tags/`, {
                method: 'PUT',
                body: JSON.stringify({"tags": tags}),
                headers: {"Content-Type": "application/json"},
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
        unlinkMap,
        unlinkDevice,
        fetchQRCode,
        fetchStatus,
        updateMapShare,
        removePoint,
        updatePointTags,
        fetchBotSetup,
        updateBotSetup,
        mapShare,
    };
};

export default useApi;
