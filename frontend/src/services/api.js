import axios from 'axios';
import config from '../config';

const api = axios.create({
  baseURL: config.apiBaseUrl,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const customError = {
      message: 'An unexpected error occurred',
      status: error.response?.status || 500,
      data: error.response?.data,
    };

    if (error.response) {
      // Server responded with error
      customError.message = error.response.data?.detail || error.response.statusText;
    } else if (error.request) {
      // Request made but no response
      customError.message = 'Unable to reach the server. Please check your connection.';
    } else {
      // Error in request setup
      customError.message = error.message;
    }

    return Promise.reject(customError);
  }
);

export const getAnalytics = async (shortCode) => {
  const response = await api.get(`/api/analytics/${shortCode}`);
  return response.data;
};

export const healthCheck = async () => {
  const response = await api.get('/health');
  return response.data;
};

// Pass frontend_base_url so the backend builds short_url with the correct domain
export const shortenURL = async (url, customAlias = null) => {
  const response = await fetch(`${config.apiBaseUrl}/api/shorten`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      url,
      custom_alias: customAlias,
      frontend_base_url: config.frontendBaseUrl,
    }),
  });

  if (!response.ok) {
    // nginx/network errors return HTML, not JSON — handle both
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to shorten URL');
    } else {
      throw new Error(`Server error: ${response.status} ${response.statusText}`);
    }
  }

  return response.json();
};

// URL comes back as JSON body which is always readable and works for any destination
export const resolveShortCode = async (shortCode) => {
  const params = new URLSearchParams({
    referer: document.referrer || '',
  });

  const response = await fetch(
    `${config.apiBaseUrl}/api/${shortCode}?${params}`,
    {
      headers: {
        // Forward the browser's user-agent explicitly in a custom header
        // since fetch automatically sends User-Agent but we re-read it server-side
        // 'X-Forwarded-User-Agent': navigator.userAgent,
      },
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Short URL not found');
  }

  const data = await response.json();
  return data.original_url;
};

export default api;