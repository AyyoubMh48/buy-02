# My Nexus and Maven work

The Nexus/Maven setup gives the six existing buy-02 Java services a private
artifact repository and shared Maven Central proxy. No Java, Spring Boot, POM
or application code changes are part of this deployment. Docker image and CI
integration remain the teammate's responsibility.

## Architecture and verified state

Compose runs the pinned official Sonatype `3.98.1` image (Nexus `3.98.1-01`),
using UID/GID 200 and the persistent `buy02-nexus-data` volume. The host
binding is `127.0.0.1` only. The restored Docker service passed health,
read/write readiness, Windows HTTP, and blob-store writability checks on
final port 8081. The native installation, its `/var/lib/nexus` data and
verified backup remain available for rollback.

Authenticated repository/user/role inventory, six SNAPSHOT publications, caching,
artifact checksum/retrieval and RBAC checks passed. Final port 8081 cutover
was explicitly approved and completed successfully. See the [completion status](NEXUS_COMPLETION_REPORT.md).

## Repository and Maven flow

`maven-releases` accepts immutable releases; `maven-snapshots` accepts
development snapshots; `maven-central` caches public dependencies; and
`maven-public` is the read group. Maven uses the reader account for dependency
resolution and the publisher account for deployment. The administrator is not
used by builds. Reader must not publish; publisher has no delete or admin
permissions.

Create credentials with `python3 scripts/nexus/setup_credentials.py`. The
helper prompts privately and writes a mode-0600 environment file outside Git.
Load it into the current shell without printing values, then follow the
[Maven runbook](NEXUS_MAVEN_RUNBOOK.md) for provisioning and verification.

The six Maven services are discovery, gateway, user-service, product-service,
media-service and order-service. The existing `manage.py` tooling audits local
configuration, provisions repositories/accounts, builds and publishes,
downloads artifacts for SHA-256 comparison, resolves versions, verifies proxy
caching and exercises access controls. All six 0.0.1-SNAPSHOT publications are confirmed and verified.

## Operations and rollback

Use `docker compose -f nexus/docker-compose.yml` for startup, health checks,
logs and stop/start. The verified endpoint and Compose default are port 8081. Never expose Nexus on a non-loopback address or
remove the named volume during routine operations.

The native service and backup are fallback assets. Stop Docker before starting
native Nexus; keep the two instances on their separate data directories. A
Docker backup must contain all of `/nexus-data`, be checksum/archive verified,
and be restored only into a separate volume during testing.
