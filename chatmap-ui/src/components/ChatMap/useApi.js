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
    const [session, setSession] = useState();
    const [status, setStatus] = useState();
    const [mapShare, setMapShare] = useState({});

    // Logout session
    const logoutSession = useCallback(async () => {
        setIsLoading(true);
        try {
            const response = await fetch(`${config.API_URL}/logout`, {
                method: 'GET',
                credentials: 'include',
            });
            if (!response.ok) throw new Error('Failed to logout');
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    });

    // Fetch map data related to a session
    const fetchMapData = useCallback(async (id) => {
        setIsLoading(true);
        setError(null);
        const url = id ? `${config.API_URL}/map/${id}` : `${config.API_URL}/map`;
        try {
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
        } catch (err) {
            // setError(err.message);
        } finally {
            setIsLoading(false);
        }
    }, [params]);

    // Fetch a new QR code for linking a device
    const fetchQRCode = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch(`${config.API_URL}/qr`, {
                method: 'GET',
                credentials: 'include',
            });
            if (!response.ok) throw new Error('Failed to fetch QR code');
            const blob = await response.blob();
            const objectURL = URL.createObjectURL(blob);
            setQRImgSrc(objectURL);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    }, []);

    // Fetch status of linking a device
    const fetchStatus = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch(`${config.API_URL}/status`, {
                method: 'GET',
                credentials: 'include',
            });
            if (!response.ok) {
                throw new Error('Failed to fetch status');
            }
            const result = await response.json();
            setStatus(result.status);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    }, []);

     // Fetch a sharing code for accessing the map
    const updateMapShare = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch(`${API_URL}/map/share`, {
                method: 'PUT',
                credentials: 'include',
            });
            if (!response.ok) {
                throw new Error('Failed to fetch share');
            }
            const result = await response.json();
            setMapShare(result);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
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
        mapShare
    };

};

export default useApi;
