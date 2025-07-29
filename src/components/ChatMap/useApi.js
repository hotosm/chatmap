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
    const [files, setFiles] = useState();
    const [QRImgSrc, setQRImgSrc] = useState();
    const [session, setSession] = useState();
    const [status, setStatus] = useState();

    const fetchSession = useCallback(async () => {
        const stored_session = localStorage.getItem("chatmap_access_token");
        if (stored_session) {
            setSession(stored_session);
        } else {
            const session_token = crypto.randomUUID();
            localStorage.setItem("chatmap_access_token", session_token);
            setSession(session_token);
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
