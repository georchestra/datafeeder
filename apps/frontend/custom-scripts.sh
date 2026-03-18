#!/bin/sh
set -e

# Executing custom scripts located in CUSTOM_SCRIPTS_DIRECTORY if environment variable is set
if [ -z "${CUSTOM_SCRIPTS_DIRECTORY}" ]; then
  echo "[INFO] No CUSTOM_SCRIPTS_DIRECTORY env variable set"
else
  echo "[INFO] CUSTOM_SCRIPTS_DIRECTORY env variable set to ${CUSTOM_SCRIPTS_DIRECTORY}"
  run-parts ${CUSTOM_SCRIPTS_DIRECTORY}/
  echo "[INFO] End executing custom scripts"
fi

if [ -z "${OVERRIDE_BASE_HREF}" ]; then
  echo "[INFO] No OVERRIDE_BASE_HREF env variable set, using default value 'dataset'"
else
  echo "[INFO] OVERRIDE_BASE_HREF env variable set to ${OVERRIDE_BASE_HREF}"
  sed -i "s|dataset|${OVERRIDE_BASE_HREF}|g" /app/datafeeder/index.html
  sed -i "s|/dataset(|/${OVERRIDE_BASE_HREF}(|g" /etc/nginx/conf.d/default.conf
fi
