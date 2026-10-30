// What the modules on the API v2 share to talk to it

// The API v2, next to the v1 the app is set up with
export const apiV2 = (apiUrl) => apiUrl.replace(/\/v\d+\/?$/, "/v2");

// The answer of the API, or null when the request fails
export const request = async (url, options = {}) => {
    try {
        const response = await fetch(url, { credentials: 'include', ...options });
        if (response.status === 204) return {};
        return response.ok ? await response.json() : null;
    } catch {
        return null;
    }
};

export const send = (method, url, body) => request(url, {
    method,
    body: body === undefined ? undefined : JSON.stringify(body),
    headers: {"Content-Type": "application/json"},
});
