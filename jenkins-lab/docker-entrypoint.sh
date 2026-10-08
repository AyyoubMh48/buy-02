#!/bin/bash

set -eu

export GITHUB_USERNAME="$(cat /run/secrets/github-username)"
export GITHUB_PAT="$(cat /run/secrets/github-pat)"
export JENKINS_ADMIN_PASSWORD="$(cat /run/secrets/jenkins-admin-password)"
export BUY01_ENV_B64="$(base64 -w 0 /run/secrets/buy01-env)"
export GATEWAY_P12_B64="$(base64 -w 0 /run/secrets/gateway-keystore.p12)"
export GATEWAY_CRT_B64="$(base64 -w 0 /run/secrets/gateway-keystore.crt)"
export GATEWAY_KEY_B64="$(base64 -w 0 /run/secrets/gateway-keystore.key)"

sonar_ready=true
for component in product user media gateway discovery frontend; do
    file="/run/secrets/sonar-${component}-token"
    if [ ! -s "$file" ]; then
        echo "Missing $file: run sonar-init and recreate Jenkins to enable analysis" >&2
        sonar_ready=false
        continue
    fi
    variable="SONAR_${component^^}_TOKEN"
    export "$variable=$(cat "$file")"
done

if [ "$sonar_ready" = false ]; then
    # Omit optional credentials entirely; never substitute empty/fake secrets.
    # JCasC retains credentials already stored in Jenkins' persistent home.
    sed '/# BEGIN SONAR CREDENTIALS/,/# END SONAR CREDENTIALS/d; /# BEGIN SONAR SERVER/,$d' \
        /casc/jenkins.yaml > /tmp/jenkins-base.yaml
    chmod 600 /tmp/jenkins-base.yaml
    chown jenkins:jenkins /tmp/jenkins-base.yaml
    export CASC_JENKINS_CONFIG=/tmp/jenkins-base.yaml
fi

exec su -s /bin/bash jenkins -c 'exec /usr/local/bin/jenkins.sh "$@"' -- "$@"
