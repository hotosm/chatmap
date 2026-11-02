// What the modules on the API v2 share to talk to it

// The API v2, next to the v1 the app is set up with
export const apiV2 = (apiUrl) => apiUrl.replace(/\/v\d+\/?$/, "/v2");

/**
 * The answer of the API with its status: { status, answer }. answer is null
 * when the request fails; status is 0 when the API did not answer.
 */
export const requestWithStatus = async (url, options = {}) => {
    try {
        const response = await fetch(url, { credentials: 'include', ...options });
        if (response.status === 204) return { status: 204, answer: {} };
        return { status: response.status, answer: response.ok ? await response.json() : null };
    } catch {
        return { status: 0, answer: null };
    }
};

// The answer of the API, or null when the request fails
export const request = async (url, options = {}) => (await requestWithStatus(url, options)).answer;

const sending = (method, body) => ({
    method,
    body: body === undefined ? undefined : JSON.stringify(body),
    headers: {"Content-Type": "application/json"},
});

export const send = (method, url, body) => request(url, sending(method, body));

// As send, with the status, for the calls that tell why they failed
export const sendWithStatus = (method, url, body) => requestWithStatus(url, sending(method, body));
