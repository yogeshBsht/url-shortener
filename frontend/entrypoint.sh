#!/bin/sh

# Overwrite the placeholder env-config.js with actual runtime values
cat <<EOF > /usr/share/nginx/html/env-config.js
window._env_ = {
  FRONTEND_BASE_URL: "${FRONTEND_BASE_URL}",
  API_BASE_URL: "${API_BASE_URL}",
  ENABLE_QR_CODE: "${ENABLE_QR_CODE}"
};
EOF

# Render nginx.conf from template — substitutes only MONITORING_PRIVATE_IP,
# explicitly scoped so envsubst doesn't touch nginx's own $host/$scheme/etc.
# runtime variables, which aren't shell env vars but are worth guarding
# against on principle.
envsubst '${MONITORING_PRIVATE_IP}' \
  < /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf

# Start nginx
exec nginx -g "daemon off;"