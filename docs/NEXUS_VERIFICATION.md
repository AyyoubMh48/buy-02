# Nexus verification record

This file records only checks performed in the current Docker migration. See
[NEXUS_COMPLETION_REPORT.md](NEXUS_COMPLETION_REPORT.md) for the concise status
and [NEXUS_MAVEN_RUNBOOK.md](NEXUS_MAVEN_RUNBOOK.md) for operational commands.

| Check | Result | Evidence |
| --- | --- | --- |
| Compose configuration | PASS | `docker compose -f nexus/docker-compose.yml config --quiet` |
| Image compatibility | PASS | Pinned Sonatype tag `3.98.1` reports Nexus `3.98.1-01` |
| Backup integrity | PASS | Recorded SHA-256 and archive verification succeeded |
| Source preservation | PASS | Backup compared against native source; native data retained |
| Docker health/readiness | PASS | Health, status and writable endpoints returned HTTP 200 at port 18081 |
| Windows browser access | PASS | Windows HTTP request returned 200 at the temporary port |
| Container identity | PASS | Runtime UID/GID is 200:200 |
| Volume writability | PASS | Restored database/blob paths writable by container process |
| Blob preservation | PASS | 3,373 blob files present; no read-only warnings observed |
| Native installation/backup retained | PASS | Native service stopped; source and archive retained |
| Maven local configuration audit | PASS | `python3 scripts/nexus/manage.py audit` |
| Nexus tooling tests | PASS | 44 tests after native-only test removal |
| Six application builds | PASS | 446 tests total; Maven Central used directly |
| Authenticated repository/RBAC inventory | PASS | Repository policies, users, least-privilege roles and access denials verified |
| Maven publish/download/cache through Nexus | PASS | Six SNAPSHOT artifacts, SHA-256 comparisons, Maven retrieval and stored proxy asset verified |
| Port 8081 cutover | BLOCKED | Awaiting explicit approval for container recreation |

No result in the blocked rows should be treated as passed. The existing Java,
Spring Boot and POM configuration was not changed for this deployment.

Final host-access rerun on 2026-11-17: all six builds PASS, 446 tests, zero failures/errors/skips. The initial sandbox run failed on socket/Mockito restrictions and was cancelled.
