#!/bin/sh

# Overwrite the placeholder env-config.js with actual runtime values
cat <<EOF > /usr/share/nginx/html/env-config.js
window._env_ = {
  FRONTEND_BASE_URL: "${FRONTEND_BASE_URL}",
  API_BASE_URL: "${API_BASE_URL}",
  ENABLE_QR_CODE: "${ENABLE_QR_CODE}"
};
EOF

# Start nginx
exec nginx -g "daemon off;"