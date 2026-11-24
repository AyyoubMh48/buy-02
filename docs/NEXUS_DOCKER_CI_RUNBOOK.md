# Ayoub — Docker registry and CI publishing

The implementation adds a Docker hosted repository, TLS reverse proxy,
least-privilege Docker accounts, image publishing/retrieval scripts and Jenkins
publishing stages. It reuses Anas's Nexus deployment and Maven tooling. Java,
Spring Boot, service POMs and application Dockerfiles are unchanged.

**Verification status:** offline regression tests and configuration checks pass.
Live Nexus/Docker push/pull and a full Jenkins run have not passed in this
environment. Starting Nexus was rejected by automatic approval review because
the earlier handoff prohibited container changes. Approve the concrete startup
below before running it here. No existing data, images or backups were deleted.

Checks completed on 2026-11-18: 69 Nexus tooling tests, 30 Jenkins configuration
tests and 16 CI helper tests pass (115 total). Both Compose overlays validate,
Nginx accepts the TLS configuration, the Jenkinsfile compiles as Groovy, shell
syntax checks pass, and documentation links/whitespace checks pass. Groovy
compilation does not replace live Jenkins Declarative Pipeline validation.
No application build/test results or real registry uploads are claimed here.

## 1. Prepare your independent Nexus

Use the [Maven onboarding runbook](NEXUS_MAVEN_RUNBOOK.md#fresh-clone-onboarding-for-teammates)
first. It covers first login, operator EULA acceptance, private credentials and
Maven provisioning. Your instance must have anonymous access disabled and the
six services must build through its Maven group. Do not import Anas's private
files or assume his backup/volume exists on your computer.

Create a local CA, server certificate and Java truststore once:

```bash
bash scripts/nexus/create_registry_tls.sh
export NEXUS_TLS_DIR="$PWD/.local/nexus-tls"
docker compose -p nexus -f nexus/docker-compose.yml -f nexus/compose.registry.yml config --quiet
```

The generator refuses to replace existing certificates. Private keys stay under
ignored `.local/`; only public CA/truststore files go to Jenkins. For an existing
installation, review the Compose diff before applying: adding a network can
recreate Nexus but retains the same named data volume. During an agreed startup
or maintenance window:

```bash
docker compose -p nexus -f nexus/docker-compose.yml -f nexus/compose.registry.yml \
  up -d --wait --wait-timeout 900
curl --cacert "$NEXUS_TLS_DIR/ca.crt" --fail https://localhost:8443/service/rest/v1/status
```

Keep the same Compose project name used for your Nexus deployment. The defaults
retain `buy02-nexus-data` and the loopback-only 8081 management binding. The
overlay adds loopback-only TLS management on 8443 and Docker registry on 5443.
Connector 8082 is internal and is never published to the host. Never use
`down -v` or restore over a live volume.

## 2. Create Docker accounts and provision the repository

Load your own Maven administrator environment privately, as documented in the
Maven runbook. Administrator credentials are needed only for provisioning.
Create a separate private file for the Docker reader and publisher:

```bash
python3 scripts/nexus/setup_docker_credentials.py
set -a
source /tmp/buy02-nexus-team.env
source .local/nexus-docker.env
set +a
export NEXUS_URL=https://localhost:8443
export NEXUS_CA_BUNDLE="$NEXUS_TLS_DIR/ca.crt"
python3 scripts/nexus/registry.py
# Review the plan before applying it to your instance:
python3 scripts/nexus/registry.py --apply
python3 scripts/nexus/registry.py --verify
unset NEXUS_ADMIN_USERNAME NEXUS_ADMIN_PASSWORD
```

Supply existing passwords for existing accounts; Enter generates passwords only
for new accounts. The file is created exclusively with mode 0600 and is never
printed. Docker provisioning preserves Maven roles/accounts and unrelated
authentication realms. It adds `DockerToken`, a `docker-hosted` repository with
immutable tags (`ALLOW_ONCE`) and these dedicated roles:

| Account | Permissions on docker-hosted |
| --- | --- |
| Docker reader | Browse/read |
| Docker publisher | Browse/read/add/edit; no delete or administration |

Configuration collisions stop the plan before writes. Live authentication is
verified by login/push/pull, not by the configuration plan alone.

## 3. Configure DNS and certificate trust

For CLI-only local testing use `localhost:5443`. For the containerized Jenkins
setup use **`nexus.buy02.test:5443` consistently**. On the Docker daemon host,
configure that hostname to resolve to `127.0.0.1` (for example, a reviewed local
hosts-file entry). Jenkins resolves it through the Compose network alias.

Both the Docker daemon and the Docker CLI process need to trust the local CA.
On a conventional Linux daemon, install the public `ca.crt` as
`/etc/docker/certs.d/nexus.buy02.test:5443/ca.crt` and into the operating system
CA store. For a localhost-only setup use the matching `localhost:5443` directory.
For Linux Docker running under RootlessKit, install the CA in the Docker
service user's configuration directory instead:

```bash
install -D -m 0644 "$NEXUS_TLS_DIR/ca.crt" \
  "${XDG_CONFIG_HOME:-$HOME/.config}/docker/certs.d/nexus.buy02.test:5443/ca.crt"
```

Use the `XDG_CONFIG_HOME` value from the daemon's environment if it differs
from your shell. The daemon still needs a DNS or hosts entry for the registry.
Verify the active daemon/context before installing the CA. A successful
`docker login` alone does not verify trust for image push and pull.

Validate HTTPS before sending credentials:

```bash
export NEXUS_DOCKER_REGISTRY=nexus.buy02.test:5443
curl --cacert "$NEXUS_TLS_DIR/ca.crt" -I "https://$NEXUS_DOCKER_REGISTRY/v2/"
```

A 401 authentication challenge is expected for an anonymous client. Its bearer
token URL must use HTTPS and a hostname/port reachable from the client and daemon.
The proxy preserves the original host and forwarded protocol for this purpose.

## 4. Build, publish and verify images

Build and test Maven services with Anas's settings. If using the local CA, Maven
needs its own Java truststore in addition to the Python CA bundle:

```bash
export MAVEN_OPTS="${MAVEN_OPTS:-} -Djavax.net.ssl.trustStore=$NEXUS_TLS_DIR/java-cacerts -Djavax.net.ssl.trustStorePassword=changeit"
python3 scripts/nexus/manage.py build all
python3 scripts/nexus/manage.py publish all
python3 scripts/nexus/images.py build --source-tag local-1
release_tag=$(python3 scripts/nexus/images.py tag --build 1)
python3 scripts/nexus/images.py publish --source-tag local-1 --tag "$release_tag" \
  --manifest reports/nexus/local-1.json
```

Gateway builds/tests require the existing application environment as described
in the root README. A successful `publish all` already builds/tests the services;
the separate build command is useful for diagnosing a new setup. Do not skip tests
to obtain a successful publication result.

Images are named `REGISTRY/buy02/SERVICE:VERSION-gCOMMIT-bBUILD`, for example
`nexus.buy02.test:5443/buy02/product-service:0.0.1-SNAPSHOT-g0123456789ab-b1`.
Use a new build number/tag for every publishing attempt. Do not overwrite tags.
The publisher uses a temporary Docker credential directory and password stdin.
After pushing, a separate reader login pulls each image by the returned SHA-256
manifest digest and checks its image ID against the original local build. Backend
images also run `java -version` without network access; this is a runtime smoke
check, not a substitute for application health tests.

The script verifies reader upload denial using a fresh probe tag, then removes
only that local probe tag. It does not delete remote artifacts. Release manifests
record Git commit, Maven coordinates, image IDs and digests, without credentials.
They are ignored by Git and archived by Jenkins. If reader verification fails
after successful uploads, retain the manifest and retry `pull`; do not republish
the same immutable tags. Publishing across services is not atomic: earlier
uploads may remain if a later upload fails. Inspect logs and choose a new release
tag when resuming an incomplete upload.

## 5. Connect Jenkins and configure credentials

JCasC creates the Nexus credentials from the machine's local files. Run the
Maven and Docker credential setup and provisioning steps first. From the repo
root, load the two private environment files created during setup. Adjust the
paths if you chose different filenames.

```bash
(
  set -eu
  umask 077
  source /tmp/buy02-nexus-team.env
  source .local/nexus-docker.env
  for account in NEXUS_READ NEXUS_PUBLISH NEXUS_DOCKER_READ NEXUS_DOCKER_PUBLISH; do
    for field in USERNAME PASSWORD; do
      key="${account}_${field}"
      test -n "${!key}" || exit 1
      printf '%s' "${!key}" > "jenkins-lab/jenkins-secrets/$key"
      chmod 600 "jenkins-lab/jenkins-secrets/$key"
    done
  done
  install -m 0600 .local/nexus-tls/ca.crt jenkins-lab/jenkins-secrets/nexus-ca.crt
  install -m 0600 .local/nexus-tls/java-cacerts jenkins-lab/jenkins-secrets/nexus-java-cacerts
)
```

Run the Bash block in Bash if your interactive shell uses a different syntax.
The default CI endpoints are listed below. To override them, write one value
per file in `jenkins-lab/jenkins-secrets/NEXUS_CI_URL` and
`jenkins-lab/jenkins-secrets/NEXUS_CI_REGISTRY`.

If the release pipeline lives in a fork, put its GitHub `owner/repository`
name in `jenkins-lab/jenkins-secrets/github-release-repository`. JCasC uses it
for `first-pipeline`. The default is `AyyoubMh48/buy-02`.

After active builds finish, rebuild Jenkins and restart it to load the files.

```bash
NEXUS_CI_NETWORK=true bash scripts/run-jenkins-host.sh
docker restart jenkins
```

The launcher adds `nexus/compose.jenkins-network.yml`, joining Jenkins to the
existing `buy02-artifacts` network. It preserves the Sonar network. The Docker
daemon still needs the host-side registry DNS and CA trust from step 3.

JCasC registers these IDs:

| ID | Kind | Value |
| --- | --- | --- |
| `nexus-url` | Secret text | `https://nexus.buy02.test:8443` |
| `nexus-maven-reader` | Username/password | Maven reader |
| `nexus-maven-publisher` | Username/password | Maven publisher |
| `nexus-docker-registry` | Secret text | `nexus.buy02.test:5443` |
| `nexus-docker-reader` | Username/password | Dedicated Docker reader |
| `nexus-docker-publisher` | Username/password | Dedicated Docker publisher |
| `nexus-ca` | Secret file | Public `.local/nexus-tls/ca.crt` |
| `nexus-java-truststore` | Secret file | `.local/nexus-tls/java-cacerts` |

Keep the local credential files out of Git. The startup
script installs the optional mounted `nexus-ca.crt` into Jenkins's OS trust store
for `docker login`. The `nexus-ca` credential configures Python,
not Docker's OS trust. The Java truststore contains default public CAs plus the
local CA, with the standard `changeit` password (it holds no private keys).

Remote CI needs a valid TLS hostname reachable by both its agent and Docker daemon,
or an appropriately configured self-hosted runner. A hosted GitHub runner cannot
reach this workstation's loopback ports. GitHub Actions continues to run quality
checks without publishing or receiving Nexus credentials.

## 6. Pipeline behavior and acceptance

The Jenkins main job already has GitHub push triggers; retain its webhook and
trusted-main SCM configuration. PR checks remain in the separate validation job.
Maven dependency/plugin resolution now uses the Nexus mirror throughout the main
pipeline. All existing tests and Sonar gates precede publishing. On main, excluding
PR and scheduled runs, Jenkins:

1. Publishes all six Maven artifacts using Anas's script, with tests enabled.
2. Builds all seven images (six backend services plus the frontend).
3. Pushes images, pulls/verifies them as the reader and archives a release manifest.
4. Deploys the retrieved images using the existing staging tags and health checks.

Build/test/gate/publishing failures stop subsequent stages. Publisher credentials
are bound only during their respective stages. A tag/digest mismatch prevents
deployment. Staging uses the existing Compose configuration: the verified digest
pull is retagged locally with the Jenkins build number, so the existing rollback
mechanism can keep selecting prior build numbers.

Before marking the integration complete, capture actual evidence for:

- Provisioning twice produces no further configuration changes.
- All six JARs and six backend images are published; the frontend also publishes
  in Jenkins so a complete staging release can be retrieved.
- Reader pulls succeed and reader uploads are denied.
- A deliberate failing test on a temporary branch prevents publishing.
- An approved main push triggers a successful complete pipeline and healthy app.
- Two different releases have distinct manifests; retrieving the earlier manifest
  restores the earlier image IDs and staging passes health/API checks.

## 7. Retrieve a previous release and troubleshoot

Download the desired `reports/nexus/release-BUILD.json` from Jenkins artifacts.
Use the Docker reader credentials, then:

```bash
python3 scripts/nexus/images.py pull --manifest reports/nexus/release-OLD_BUILD.json
```

This retrieves pinned images and restores `SERVICE:OLD_BUILD` tags. It does not
change running containers. Deploy that build through the existing staging Compose
procedure in the root README, selecting its `APP_IMAGE_TAG`, then check container
health and the real catalog API. Never edit the archived manifest to choose a
different digest. Keep previous manifests for traceability.

| Failure | Action |
| --- | --- |
| DNS/connectivity | Check daemon context, local hosts entry, Jenkins network and loopback ports |
| Unknown CA | Install the public CA for both CLI and daemon; check Java truststore and Python bundle separately |
| HTTP token URL | Check proxy forwarded host/protocol; never send registry credentials over remote HTTP |
| 401/403 | Check correct Docker versus Maven account, DockerToken realm and repository permissions |
| Immutable tag conflict | Use a new build/tag; preserve the original release |
| Missing JAR/dist | Finish Maven/frontend build before Docker build |
| Missing Jenkins credential | Add the exact credential IDs above; never substitute administrator credentials |
| Partial publication | Preserve successful uploads/logs; do not delete artifacts to retry |
| Digest/image-ID mismatch | Stop deployment and inspect the manifest and registry; do not bypass verification |

References: [Sonatype Docker authentication](https://help.sonatype.com/en/docker-authentication.html),
[reverse proxy guidance](https://help.sonatype.com/en/docker-repository-reverse-proxy-strategies.html),
[Docker login](https://docs.docker.com/reference/cli/docker/login/),
[Docker CA trust](https://docs.docker.com/engine/security/certificates/).
