import { useState, useCallback } from "react";

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Get ChatMap data from an API
 *
 * @param {object} params - Parameters
 */
const useApi = (params = {}) => {

    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);
    const [mapData, setMapData] = useState({
        type: "FeatureCollection",
        features: []
    });
    const [files, setFiles] = useState(null);
    const [QRImgSrc, setQRImgSrc] = useState(null);
    const [session, setSession] = useState(null);
    const [status, setStatus] = useState(null);

    const fetchSession = useCallback(async (session_token) => {
        const local_session = session_token || localStorage.getItem("chatmap_access_token");
        if (local_session) {
            setSession(local_session);
            localStorage.setItem("chatmap_access_token", local_session);
        }
        return;
    }, []);

    const fetchMapData = useCallback(async () => {
        const token = localStorage.getItem("chatmap_access_token")
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch(`${API_URL}/chatmap?user_id=${token}`, {
                method: 'GET',
            });
            if (!response.ok) throw new Error('Failed to fetch data');
            const result = await response.json();
            setMapData(result);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    }, [params]);

    const fetchQRCode = useCallback(async () => {
        const token = localStorage.getItem("chatmap_access_token")
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch(`${API_URL}/qr?user_id=${token}`, {
                method: 'GET',
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
        const token = localStorage.getItem("chatmap_access_token")
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch(`${API_URL}/status?user_id=${token}`, {
                method: 'GET'
            });
            if (!response.ok) throw new Error('Failed to fetch status');
            const result = await response.json();
            setStatus(result.status);
        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    }, []);

    return { mapData, QRImgSrc, session, status, files, isLoading, error, fetchMapData, fetchSession, fetchQRCode, fetchStatus };

};

export default useApi;
