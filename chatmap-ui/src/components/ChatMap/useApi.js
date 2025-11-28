import { useState, useCallback } from "react";

/**
 * Get ChatMap data from an API
 *
 * @param {object} params - Parameters
 */
const useApi = (params = {}) => {

    const API_URL = window._CHATMAP_CONFIG("API_URL", 'http://localhost:8000/api');

    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [mapData, setMapData] = useState({
        type: "FeatureCollection",
        features: []
    });
    const [QRImgSrc, setQRImgSrc] = useState();
    const [session, setSession] = useState();
    const [status, setStatus] = useState();

    const logoutSession = useCallback(async () => {
        setIsLoading(true);
        const token = sessionStorage.getItem("chatmap_access_token")
        try {
            const response = await fetch(`${API_URL}/logout`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            if (!response.ok) throw new Error('Failed to logout');
            sessionStorage.removeItem("chatmap_access_token");
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    });

    const fetchSession = useCallback(async () => {
        const stored_session = sessionStorage.getItem("chatmap_access_token");
        if (stored_session) {
            setSession(stored_session);
        } else {
            setIsLoading(true);
            setError(null);
            try {
                const response = await fetch(`${API_URL}/get-token`, {
                    method: 'GET',
                });
                if (!response.ok) throw new Error('Failed to fetch data');
                const result = await response.json();
                sessionStorage.setItem("chatmap_access_token", result.access_token);
                setSession(result.access_token);
            } catch (err) {
                setError(err.message);
            } finally {
                setIsLoading(false);
            }
        }
        return;
    }, []);

    const fetchMapData = useCallback(async () => {
        const token = sessionStorage.getItem("chatmap_access_token")
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch(`${API_URL}/map`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
            });
            if (response.status === 401) {
                console.log("Session expired")
                sessionStorage.removeItem("chatmap_access_token");
                setSession();
                setStatus();
                setMapData();
                await fetchQRCode();
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

    const fetchQRCode = useCallback(async () => {
        const token = sessionStorage.getItem("chatmap_access_token")
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch(`${API_URL}/qr`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
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

    const fetchStatus = useCallback(async () => {
        const token = sessionStorage.getItem("chatmap_access_token")
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch(`${API_URL}/status`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
            });
            if (!response.ok) {
                if (response.status === 401) {
                    sessionStorage.removeItem("chatmap_access_token");
                    fetchSession();
                }
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

    return {
        mapData,
        QRImgSrc,
        session,
        status,
        isLoading,
        error,
        fetchMapData,
        fetchSession,
        logoutSession,
        fetchQRCode,
        fetchStatus
    };

};

export default useApi;
