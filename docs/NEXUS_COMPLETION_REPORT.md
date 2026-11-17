# Nexus completion status

Updated: 2026-11-17. Docker Compose is the supported project deployment. No
credentials, artifacts or live Nexus configuration have been changed by this
documentation cleanup.

## Verified

- Backup: `/var/backups/nexus/native-3.98.1-01-20261117T115025Z.tar`, SHA-256
  `6e191d2ae6b34e798b0ecef0b5c9f3b4935ae1101e66a125802f0ffeb169dfdf`;
  archive integrity and comparison to preserved native data passed.
- Docker Nexus 3.98.1-01 runs from `sonatype/nexus3:3.98.1` with UID/GID 200,
  persistent volume `buy02-nexus-data`, and localhost-only binding.
- Temporary endpoint `127.0.0.1:18081` passed health, read/write readiness and
  Windows HTTP checks. Restored blob data was writable and 3,373 blob files were
  present; no read-only blob-store warnings were observed.
- Docker Compose validation and `manage.py audit` passed.
- Six existing Maven services passed `clean verify`: discovery 2 tests,
  gateway 27, user-service 48, product-service 93, media-service 45,
  order-service 231; 446 total, zero failures/errors/skips. These builds used
  Maven Central directly, not Nexus.
- Nexus tooling tests passed: 33 tests after removal of native-only downloader
  and health-check tests.

## Pending

- Authenticated repository, account, role and component inventory.
- Provisioning/reconciliation of the four Maven repositories and least-privilege
  reader/publisher accounts.
- Maven builds through Nexus, six SNAPSHOT publishes, artifact download/checksum
  verification, dependency cache and RBAC checks.
- Final cutover to port 8081. The current instance remains at 18081; explicit
  operator approval is required before cutover.

The interactive helper is `scripts/nexus/setup_credentials.py`; it creates an
external mode-0600 file at `/tmp/nexus-migration-credentials.env` and refuses
to overwrite it. No secret values are stored in Git. After credentials are
configured, follow [the runbook](NEXUS_MAVEN_RUNBOOK.md) and update this report
with actual command results.

The native `/var/lib/nexus`, systemd service and verified archive remain intact
for rollback. Do not remove them or the Docker volume until migration,
publishing, authentication, persistence and restore validation are complete.
CI and Docker image integration remain the teammate's responsibility.

## Final execution checkpoint

- Fresh onboarding Compose started successfully on localhost 28081 using the
  separate `buy02-nexus-onboarding-data` volume and `buy02-nexus-onboarding`
  container. The current migrated service and volume were not changed.
- Isolated admin authentication and private password rotation passed. Repository
  provisioning, a second no-change provisioning plan and `verify-config` passed.
- Isolated Maven publish initially FAILED with 403. Diagnosis confirmed the
  fresh instance's EULA is unaccepted, including for admin artifact requests.
  The operator must accept it in the browser. No EULA was accepted automatically.
  Fresh-instance upload/download/cache/RBAC remain BLOCKED pending that step.
- The existing 18081 service is healthy, writable and UID/GID 200. Its private
  credential file is absent. `setup_credentials.py --finish` now completes the
  authenticated workflow locally after private entry; `--reuse --finish` resumes
  without overwriting the private file. No current-instance publish is confirmed.
- 33 tooling tests, Compose validation for ports 8081/18081, local audit, Python
  syntax, scoped whitespace check and tracked secret/data signature scans PASS.
- An application rerun in the sandbox failed due socket/Mockito restrictions;
  it was cancelled and rerun with host access. Final host results are recorded
  below when complete. The historical 446-test result above predates this rerun.
- Full-worktree `git diff --check` FAILS on pre-existing CRLF/trailing whitespace
  in unrelated changes (also fails with CRLF tolerated). Nexus-scoped check
  PASSES. Those teammate changes were not edited or staged. The worktree has
  hundreds of pre-existing modifications; use scoped staging only.
- Default Secret Encryption Key warning is deferred. No encryption-key changes,
  final cutover, commits, pushes or merges were performed. The isolated test
  volume/container are retained; no test or existing volume was deleted.


Final host-access rerun: all six clean verify builds PASS. 446 tests, zero failures/errors/skips (from Surefire XML). Direct Maven Central resolution was used, not Nexus.

- discovery: {'tests': 2, 'failures': 0, 'errors': 0, 'skipped': 0}
- gateway: {'tests': 27, 'failures': 0, 'errors': 0, 'skipped': 0}
- user-service: {'tests': 48, 'failures': 0, 'errors': 0, 'skipped': 0}
- product-service: {'tests': 93, 'failures': 0, 'errors': 0, 'skipped': 0}
- media-service: {'tests': 45, 'failures': 0, 'errors': 0, 'skipped': 0}
- order-service: {'tests': 231, 'failures': 0, 'errors': 0, 'skipped': 0}
