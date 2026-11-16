#!/usr/bin/env bash
# Fresh native Linux x86-64 installation. Never migrates an existing Nexus.
set -euo pipefail
umask 027
version=3.98.1-01
sha256=a8b204c50708729492380697c1d64f342281468ddfd96e1ab199de86a478e768
archive="nexus-${version}-linux-x86_64.tar.gz"
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
die() { echo "ERROR: $*" >&2; exit 1; }
[[ $EUID -eq 0 ]] || die 'Run with sudo on the intended Nexus host.'
[[ $(uname -m) == x86_64 && $(uname -s) == Linux ]] || die 'This pinned installer supports Linux x86-64 only.'
[[ -d /run/systemd/system ]] || die 'A running systemd host is required (this shell/container is insufficient).'
for tool in curl tar sha256sum python3 systemctl useradd groupadd getent install flock stat mktemp cp mv; do
  command -v "$tool" >/dev/null || die "Install the missing prerequisite: $tool"
done
exec 9>/run/lock/buy02-nexus-install.lock
flock -n 9 || die 'Another installation is in progress.'
if [[ -f /opt/nexus-${version}/.buy02-managed && -L /opt/nexus ]]; then
  [[ $(readlink -f /opt/nexus) == /opt/nexus-${version} ]] || die 'Unexpected Nexus symlink; inspect manually.'
  systemctl enable --now nexus.service nexus-healthcheck.timer
  /usr/local/libexec/nexus-healthcheck --wait
  exit 0
fi
for existing in /opt/nexus /opt/nexus-${version} /var/lib/nexus /etc/systemd/system/nexus.service; do
  [[ ! -e $existing && ! -L $existing ]] || die "Existing $existing found. Back up and review manually; refusing to replace it."
done
# Unlike extraction scratch space, this cache survives failures and interrupts.
cache_dir=/var/cache/nexus/downloads
[[ ! -L /var/cache/nexus && ! -L $cache_dir ]] || die 'Refusing a symlink download cache.'
install -d -o root -g root -m 0750 /var/cache/nexus "$cache_dir"
echo "Downloading Nexus ${version}; retaining partial transfers under $cache_dir."
bash "$source_dir/download.sh" \
  "https://download.sonatype.com/nexus/3/${archive}" "$sha256" "$cache_dir/$archive" \
  "${NEXUS_PARTIAL_ARCHIVE:-}"
# Defense in depth: extraction is gated on the trusted checksum here as well.
printf '%s  %s\n' "$sha256" "$cache_dir/$archive" | sha256sum --check --status || die 'Archive checksum mismatch; refusing extraction.'
work=$(mktemp -d)
# Never remove the persistent download cache or any Nexus data in cleanup.
trap 'rm -rf -- "$work"' EXIT
tar --extract --gzip --file "$cache_dir/$archive" --directory "$work" --no-same-owner
bundle="$work/nexus-${version}"
[[ -x $bundle/bin/nexus && -f $bundle/bin/nexus.vmoptions ]] || die 'Unexpected vendor archive layout; review before installing.'
if getent passwd nexus >/dev/null; then
  [[ $(id -u nexus) != 0 ]] || die 'The nexus user must not be root.'
  [[ $(getent passwd nexus | cut -d: -f7) =~ /(nologin|false)$ ]] || die 'Existing nexus account must have a non-login shell.'
else
  getent group nexus >/dev/null || groupadd --system nexus
  useradd --system --gid nexus --home-dir /var/lib/nexus --no-create-home --shell /usr/sbin/nologin nexus
fi
getent group nexus >/dev/null || die 'The nexus group is missing.'
install -d -o nexus -g nexus -m 0750 /var/lib/nexus
install -d -o nexus -g nexus -m 0750 /var/lib/nexus/{etc,log,tmp,javaprefs}
# Preserve vendor JVM flags and its bundled runtime, replacing only storage paths.
python3 - "$bundle/bin/nexus.vmoptions" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
text = p.read_text()
text = text.replace('../sonatype-work/nexus3', '/var/lib/nexus')
overrides = {'-Dkaraf.data=': '/var/lib/nexus',
             '-Dkaraf.log=': '/var/lib/nexus/log',
             '-Djava.io.tmpdir=': '/var/lib/nexus/tmp',
             '-Djava.util.prefs.userRoot=': '/var/lib/nexus/javaprefs'}
lines = [line for line in text.splitlines() if not any(line.startswith(k) for k in overrides)]
lines += [key + value for key, value in overrides.items()]
p.write_text('\n'.join(lines) + '\n')
PY
printf 'run_as_user="nexus"\n' > "$bundle/bin/nexus.rc"
install -m 0640 -o nexus -g nexus "$source_dir/nexus.properties" /var/lib/nexus/etc/nexus.properties
chown -R root:nexus "$bundle"
chmod -R g-w,o-rwx "$bundle"
mv -- "$bundle" "/opt/nexus-${version}"
ln -s "/opt/nexus-${version}" /opt/nexus
install -d -m 0755 /usr/local/libexec
install -m 0755 "$source_dir/healthcheck.sh" /usr/local/libexec/nexus-healthcheck
for unit in nexus.service nexus-healthcheck.service nexus-healthcheck.timer; do
  install -m 0644 "$source_dir/systemd/$unit" "/etc/systemd/system/$unit"
done
systemctl daemon-reload
touch "/opt/nexus-${version}/.buy02-managed"
systemctl enable --now nexus.service nexus-healthcheck.timer
/usr/local/libexec/nexus-healthcheck --wait
echo 'Nexus HTTP readiness verified at http://127.0.0.1:8081/ .'
echo 'Complete the first-login wizard using /var/lib/nexus/admin.password; do not copy this password into Git or logs.'
