# Nexus/Maven completion report

Updated: 2026-11-17. Owner: **Anas**. The Nexus/Maven implementation is complete
and verified on temporary localhost port 18081. Final port 8081 cutover is
prepared but has not been executed; container recreation requires approval.

## Verified results

| Check | Result | Evidence |
| --- | --- | --- |
| Six full application builds/tests | PASS | Previous host-access clean verify: 446 tests, zero failures/errors/skips; Java, Spring Boot and POM versions preserved |
| Nexus tooling tests | PASS | 44 tests, including cache path/checksum/retry and SNAPSHOT inventory regressions |
| Compose validation | PASS | Existing and final localhost port configurations validated |
| Maven configuration audit | PASS | Six POM coordinates, deployment IDs and settings mirror checked |
| Administrator authentication/configuration | PASS | Four required Maven repositories, reader/publisher accounts, roles and anonymous-access restrictions verified |
| Existing SNAPSHOT inventory | PASS | All six found through repository-scoped Maven groupId/artifactId/baseVersion queries |
| Artifact downloads/checksums | PASS | JAR and POM bytes match hosted/group/local SHA-256 for all six |
| Maven version retrieval | PASS | All six 0.0.1-SNAPSHOT artifacts resolved through Nexus in the prior authenticated verification |
| Proxy caching | PASS | Repeated group/proxy downloads match the stored maven-central asset's SHA-256 |
| Non-destructive RBAC | PASS | Reader/publisher downloads allowed; anonymous download, reader upload and publisher user administration denied; no DELETE requests |
| Runtime | PASS | Healthy, writable, non-root UID/GID 200, 127.0.0.1:18081 with buy02-nexus-data |
| Git secret/data scans | PASS | Current tracked content/path checks found no private credential files, archives, databases or secret signatures |
| Scoped diff whitespace | PASS | Nexus files and updated documentation pass |
| Entire worktree whitespace | FAIL | Pre-existing unrelated CRLF/trailing whitespace; those files were not modified by this cleanup |

## Published artifacts

All listed base versions are **0.0.1-SNAPSHOT** in **maven-snapshots**. Nexus
stores timestamped builds beneath these base versions. Latest checks only read
existing artifacts; nothing was republished or overwritten.

| Service | Maven coordinate |
| --- | --- |
| discovery | com.buy01:discovery:0.0.1-SNAPSHOT |
| gateway | com.buy01:gateway:0.0.1-SNAPSHOT |
| user-service | com.buy01:user-service:0.0.1-SNAPSHOT |
| product-service | com.buy01:product-service:0.0.1-SNAPSHOT |
| media-service | com.buy-01:media:0.0.1-SNAPSHOT |
| order-service | com.buy01:order-service:0.0.1-SNAPSHOT |

The cache verification failure was caused by comparing paths without accounting
for Nexus's leading slash. Verification now normalizes that slash, checks the
stored proxy asset SHA-256 and permits bounded retries (1, 2, 4 seconds).
Matching download bytes alone cannot pass. The helper's final inventory filter
now uses `maven.baseVersion`, which correctly finds timestamped SNAPSHOT builds.

## Responsibility handoff

- **Anas — completed:** Docker Compose deployment of Nexus, Maven repository
  provisioning, Maven publishing/retrieval/versioning, dependency proxy/cache,
  credentials and least-privilege RBAC, verification and Nexus documentation.
- **Ayoub — integration responsibility:** application Dockerfiles/images,
  Docker image publishing/retrieval and CI/CD integration. No application
  Dockerfiles or CI pipelines were modified by this cleanup.
- **Approval pending:** recreate only the Nexus container on port 8081, retain
  buy02-nexus-data, then recheck Windows HTTP, health, UID/GID, writability and
  all six stored artifacts. The running container remains on port 18081.

CI inputs: NEXUS_URL, NEXUS_READ_USERNAME, NEXUS_READ_PASSWORD,
NEXUS_PUBLISH_USERNAME and NEXUS_PUBLISH_PASSWORD. Administrator credentials
must never be supplied to Maven/CI. Remote CI needs an authenticated TLS endpoint
or SSH tunnel; do not broaden the localhost bind.

## Preserved data and deferred work

The native installation and `/var/lib/nexus` are preserved. The verified archive
`/var/backups/nexus/native-3.98.1-01-20261117T115025Z.tar` remains available;
recorded SHA-256:
`6e191d2ae6b34e798b0ecef0b5c9f3b4935ae1101e66a125802f0ffeb169dfdf`.
No container restart, port change, credential reset or data migration occurred
in this cleanup. No artifacts, volumes or backups were deleted.

Fresh Compose startup, private admin setup and idempotent provisioning were
verified in the separate onboarding instance on port 28081. Its end-to-end
publish test remains subject to operator EULA acceptance; it is distinct from
the fully verified migrated instance on 18081. The test volume is retained.

The Default Secret Encryption Key warning is deferred security work. Encryption
keys and secret storage were not changed. Full-worktree whitespace cleanup is
outside Anas's Nexus scope; stage only the reviewed Nexus changes. No automatic
commit, push or merge was performed.

See [NEXUS_MAVEN_RUNBOOK.md](NEXUS_MAVEN_RUNBOOK.md) for onboarding, backup,
rollback, CI endpoints and exact cutover commands awaiting approval.
