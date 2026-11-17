# Nexus deployment and scripts

Docker Compose is the supported Nexus deployment. This guide inventories the
remaining project files and the task each one serves.

## File classification

| File | Classification | Purpose |
| --- | --- | --- |
| `nexus/docker-compose.yml` | KEEP | Pinned official image, localhost-only port, persistent volume and health check |
| `nexus/maven/settings.xml` | KEEP | Maven mirror and authenticated deployment IDs |
| `nexus/repositories.json` | KEEP | Desired hosted, proxy and group repository definitions |
| `nexus/env.example` | KEEP | Variable names and non-secret examples only |
| `nexus/.gitignore` | KEEP | Excludes local env, secret, data and download files |
| `scripts/nexus/manage.py` | KEEP | Audit, provisioning, builds, publishing, cache, retrieval and RBAC checks |
| `scripts/nexus/nexus_api.py` | KEEP | Authenticated REST client that avoids logging credentials/response bodies |
| `scripts/nexus/test_nexus.py` | KEEP | Unit and safety tests for Nexus tooling |
| `scripts/nexus/setup_credentials.py` | KEEP | Private interactive setup; exclusive mode-0600 file creation outside Git |
| `README.md` and Nexus docs | UPDATE | Current Docker workflow, evidence and remaining authenticated work |
| Native installer, downloader, health check, systemd units and native properties | REMOVE | Superseded native deployment implementation; data/service are retained on host |
| `scripts/nexus/test_download.py` | REMOVE | Tested only the obsolete native archive downloader |

## Compose operations

From the repository root:

```bash
docker compose -f nexus/docker-compose.yml config --quiet
NEXUS_HOST_PORT=18081 docker compose -f nexus/docker-compose.yml up -d --wait --wait-timeout 900
docker compose -f nexus/docker-compose.yml ps
docker compose -f nexus/docker-compose.yml logs --tail=100 nexus
docker inspect buy02-nexus --format '{{.State.Health.Status}}'
docker exec buy02-nexus id
```

The official tag `sonatype/nexus3:3.98.1` contains Nexus `3.98.1-01`. Compose
uses the image's default UID/GID 200, persistent named volume
`buy02-nexus-data`, a health check for status and writable readiness, and a
127.0.0.1-only published port. The temporary verified endpoint is 18081; the
default is 8081. Compose creates the named volume when absent.
`NEXUS_CONTAINER_NAME` and `NEXUS_VOLUME_NAME` allow isolated onboarding tests.
Cutover is still pending approval.

## Maven configuration and security

The four desired repositories are declared in `nexus/repositories.json`:
immutable hosted releases (`ALLOW_ONCE`), hosted snapshots (`ALLOW`), the Maven
Central proxy and the public read group. `settings.xml` mirrors all dependency
and plugin retrieval through `maven-public`; Maven gets credentials from
environment variables, not from committed settings.

`setup_credentials.py` privately prompts for admin, reader and publisher
credentials, then creates `/tmp/nexus-migration-credentials.env` with mode
0600. It does not overwrite an existing file. Keep it outside Git. Reader gets
read access through the group; publisher gets read/add/edit on hosted
repositories and no delete/admin privileges. Admin credentials are only for
configuration. Current live repository and RBAC state is pending authenticated
verification.

## Existing tooling

Run `python3 scripts/nexus/manage.py audit` for local XML/coordinate checks.
`provision` prints a plan; `provision --apply` reconciles the plan. `verify-config`
checks server state. `build all` builds/tests six services through Nexus;
`publish all` deploys their current POM artifacts and downloads/checksums them.
`resolve SERVICE` retrieves a selected version; `cache` verifies a Maven Central
artifact through the proxy/group; `verify-access` checks allowed and denied
operations. Review the runbook before applying configuration or publishing.

The tooling test suite is `python3 -m unittest discover -s scripts/nexus -p
'test_*.py' -v`. The current recorded result is 33 tests passed.

## Backup and fallback

The complete migration archive and original `/var/lib/nexus` are retained
outside Git. Back up Docker only from a consistent stopped service; include all
of `/nexus-data`, verify checksum/archive integrity, and test restores in a new
volume. For rollback, stop Docker first and start the preserved native service.
Never point both Nexus processes at one writable data directory. See the
[runbook](NEXUS_MAVEN_RUNBOOK.md) for checks and current blockers.
