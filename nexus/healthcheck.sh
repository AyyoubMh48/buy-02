#!/usr/bin/env bash
set -euo pipefail
attempts=1
[[ ${1:-} == --wait ]] && attempts=120
deadline=$((SECONDS + 600))
for ((try=1; try<=attempts; try++)); do
  if curl --fail --silent --show-error --max-time 4 --noproxy '*' \
      http://127.0.0.1:8081/service/rest/v1/status >/dev/null 2>&1 &&
     curl --fail --silent --show-error --max-time 4 --noproxy '*' \
      http://127.0.0.1:8081/service/rest/v1/status/writable >/dev/null 2>&1; then
    echo 'Nexus is ready for reads and writes.'
    exit 0
  fi
  if ((SECONDS >= deadline)); then break; fi
  if ((try < attempts)); then sleep 4; fi
done
echo 'Nexus readiness failed. Check systemctl status nexus and /var/lib/nexus/log/nexus.log.' >&2
exit 1
