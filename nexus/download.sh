#!/usr/bin/env bash
# Download one pinned HTTPS archive. Never extract it or touch Nexus data.
# Usage: bash download.sh URL SHA256 DESTINATION [EXISTING_PARTIAL]
set -euo pipefail
umask 027
die() { echo "ERROR: $*" >&2; exit 1; }
[[ $# -ge 3 && $# -le 4 ]] || die 'Usage: download.sh URL SHA256 DESTINATION [EXISTING_PARTIAL]'
url=$1
checksum=$2
destination=$3
import_partial=${4:-}
[[ $url == https://* && $url != *$'\n'* && $url != *$'\r'* ]] || die 'The download requires an HTTPS URL.'
[[ $checksum =~ ^[a-f0-9]{64}$ ]] || die 'A pinned SHA-256 is required.'
[[ -d $(dirname -- "$destination") ]] || die 'Create the download cache directory first.'
partial="${destination}.part"
source_file="${destination}.source"
for path in "$destination" "$partial" "$source_file" "${destination}.lock"; do
  [[ ! -L $path && ( ! -e $path || -f $path ) ]] || die "Refusing a symlink or non-regular cache file: $path"
done
exec 8>>"${destination}.lock"
flock -n 8 || die 'Another process is using this archive download.'
verified() {
  [[ -f $1 ]] && printf '%s  %s\n' "$checksum" "$1" | sha256sum --check --status
}
preserve_rejected() {
  local saved
  saved=$(mktemp "${1}.rejected.XXXXXX")
  mv -T -- "$1" "$saved"
  echo "Preserved rejected download at $saved" >&2
}
if verified "$destination"; then
  echo "Reusing checksum-verified archive: $destination"
  exit 0
fi
if [[ -e $destination ]]; then
  preserve_rejected "$destination"
fi
if verified "$partial"; then
  mv -T -- "$partial" "$destination"
  echo "Archive SHA-256 verified: $destination"
  exit 0
fi
expected_source=$(printf '%s\n%s' "$url" "$checksum")
if [[ -f $partial && ( ! -f $source_file || $(cat -- "$source_file") != "$expected_source" ) ]]; then
  # Unbound bytes must never be appended to a different URL/version/checksum.
  preserve_rejected "$partial"
fi
source_temp=$(mktemp "${source_file}.XXXXXX")
printf '%s\n%s\n' "$url" "$checksum" > "$source_temp"
mv -T -- "$source_temp" "$source_file"
if [[ -n $import_partial && ! -f $partial ]]; then
  [[ -f $import_partial && ! -L $import_partial && -r $import_partial ]] || die 'The supplied partial must be a readable, regular, non-symlink file.'
  import_temp=$(mktemp "${partial}.import.XXXXXX")
  # Retain the original recovery file; only a private cache copy is resumed.
  cp -- "$import_partial" "$import_temp"
  mv -T -- "$import_temp" "$partial"
  echo 'Copied the supplied partial into the cache; full validity will be checked against the pinned checksum.'
fi
delay=2
restarted=false
for ((attempt=1; attempt<=5; attempt++)); do
  # Includes recovery from interruption after all bytes arrived but before rename.
  if verified "$partial"; then
    mv -T -- "$partial" "$destination"
    echo "Archive SHA-256 verified: $destination"
    exit 0
  fi
  offset=0
  [[ ! -f $partial ]] || offset=$(stat -c %s -- "$partial")
  echo "Download attempt $attempt/5; resuming at byte $offset."
  result=0
  # Retry here, rather than inside curl, so every attempt recalculates the latest
  # on-disk offset and retains bytes received before a reset (including exit 56).
  http_code=$(curl --disable --fail --location --max-redirs 5 --show-error \
    --proto '=https' --proto-redir '=https' --tlsv1.2 \
    --connect-timeout 20 --max-time 1800 --speed-limit 1024 --speed-time 60 \
    --retry 0 --continue-at - --output "$partial" --write-out '%{http_code}' \
    "$url") || result=$?
  if verified "$partial"; then
    mv -T -- "$partial" "$destination"
    echo "Archive SHA-256 verified: $destination"
    exit 0
  fi
  # Do not move the final retained partial away when no attempt remains to
  # restart it. The next invocation can resume or safely restart that candidate.
  if ((attempt == 5)); then break; fi
  if ((result == 0)); then
    # A complete but wrong body may be a stale/corrupt partial or changed remote.
    if [[ $restarted == true ]]; then
      die "SHA-256 mismatch after a fresh transfer. No extraction allowed; inspect $partial and the pinned source/checksum."
    fi
    echo 'SHA-256 mismatch. Preserving the candidate and allowing one fresh transfer.' >&2
    preserve_rejected "$partial"
    restarted=true
  elif ((offset > 0)) && { ((result == 33)) || [[ $http_code == 416 ]]; }; then
    echo 'Server refused the range request. Restarting only this incomplete download.' >&2
    preserve_rejected "$partial"
    restarted=true
  elif [[ $result == 60 || $result == 51 || $result == 3 || $result == 1 || $result == 23 ]]; then
    die "curl exit $result; check TLS, URL or local file access. Partial retained; no extraction allowed."
  elif [[ $result == 22 && $http_code == 4?? && $http_code != 408 && $http_code != 429 ]]; then
    die "HTTP $http_code; partial retained. Check the pinned URL; no extraction allowed."
  fi
  if ((attempt < 5)); then
    echo "Transfer not verified (curl $result, HTTP $http_code). Retrying in ${delay}s; downloaded bytes are retained." >&2
    sleep "$delay"
    delay=$((delay * 2))
  fi
done
die "Download not verified after 5 attempts. Partial retained at $partial; rerun the same command to resume. No extraction allowed."
