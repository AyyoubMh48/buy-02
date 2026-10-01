#!/bin/bash

set -eu

export GITHUB_USERNAME="$(cat /run/secrets/github-username)"
export GITHUB_PAT="$(cat /run/secrets/github-pat)"
export JENKINS_ADMIN_PASSWORD="$(cat /run/secrets/jenkins-admin-password)"
export BUY01_ENV_B64="$(base64 -w 0 /run/secrets/buy01-env)"
export GATEWAY_P12_B64="$(base64 -w 0 /run/secrets/gateway-keystore.p12)"
export GATEWAY_CRT_B64="$(base64 -w 0 /run/secrets/gateway-keystore.crt)"
export GATEWAY_KEY_B64="$(base64 -w 0 /run/secrets/gateway-keystore.key)"

exec su -s /bin/bash jenkins -c 'exec /usr/local/bin/jenkins.sh "$@"' -- "$@"