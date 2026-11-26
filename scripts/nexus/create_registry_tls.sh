#!/usr/bin/env bash
# Generate private local-lab certificates and a Java truststore without replacing files.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
tls_dir=${1:-.local/nexus-tls}
for tool in openssl keytool; do
    command -v "$tool" >/dev/null || { echo "Missing $tool" >&2; exit 1; }
done
test ! -e "$tls_dir" || { echo 'Certificate directory already exists; refusing to overwrite it.' >&2; exit 1; }
umask 077
mkdir -p "$tls_dir"
openssl req -x509 -newkey rsa:3072 -sha256 -nodes -days 365 \
    -keyout "$tls_dir/ca.key" -out "$tls_dir/ca.crt" -subj '/CN=Buy02 Local Registry CA' \
    -addext 'basicConstraints=critical,CA:TRUE' -addext 'keyUsage=critical,keyCertSign,cRLSign'
openssl req -new -newkey rsa:3072 -nodes -keyout "$tls_dir/server.key" \
    -out "$tls_dir/server.csr" -subj '/CN=nexus.buy02.test'
cat > "$tls_dir/server.ext" <<'EOF'
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=DNS:localhost,DNS:nexus.buy02.test,DNS:nexus-tls,IP:127.0.0.1
EOF
openssl x509 -req -in "$tls_dir/server.csr" -CA "$tls_dir/ca.crt" -CAkey "$tls_dir/ca.key" \
    -CAcreateserial -out "$tls_dir/server.crt" -days 365 -sha256 -extfile "$tls_dir/server.ext"
java_bin=$(readlink -f "$(command -v java)")
cp "$(dirname "$java_bin")/../lib/security/cacerts" "$tls_dir/java-cacerts"
keytool -importcert -noprompt -alias buy02-nexus-local-ca -file "$tls_dir/ca.crt" \
    -keystore "$tls_dir/java-cacerts" -storepass changeit
# Public trust material must be readable by the Jenkins process; keys remain 0600.
chmod 644 "$tls_dir/ca.crt" "$tls_dir/server.crt" "$tls_dir/java-cacerts"
openssl verify -CAfile "$tls_dir/ca.crt" "$tls_dir/server.crt"
echo "Created local TLS material in $tls_dir. Keep the CA/server private keys out of Git and CI."
