const config = {
  frontendBaseUrl:
    window._env_?.FRONTEND_BASE_URL ||
    process.env.REACT_APP_FRONTEND_BASE_URL ||
    window.location.origin,

  apiBaseUrl:
    window._env_?.API_BASE_URL ||
    process.env.REACT_APP_API_BASE_URL ||
    "http://localhost:8000",

  enableQRCode:
    window._env_?.ENABLE_QR_CODE === "true" ||
    process.env.REACT_APP_ENABLE_QR_CODE === "true",
};

export default config;