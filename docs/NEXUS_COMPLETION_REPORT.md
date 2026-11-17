# Nexus follow-up: completed work and remaining execution

## Temporary Docker migration phase — 2026-11-17

**Backup verified:** `/var/backups/nexus/native-3.98.1-01-20261117T115025Z.tar`,
SHA-256 `6e191d2ae6b34e798b0ecef0b5c9f3b4935ae1101e66a125802f0ffeb169dfdf`,
3,521 archive entries. A second checksum and tar comparison passed, including
comparison against the still-untouched `/var/lib/nexus` source.

**Temporary Docker instance verified:** Sonatype image tag `3.98.1` resolved to
Nexus `3.98.1-01` (amd64); the image declares user `nexus`, runtime UID/GID
200:200. The new `buy02-nexus-data` volume contains the restored data (3,469
files; about 193 MiB). Only the copied listener changed from `127.0.0.1` to
`0.0.0.0` inside the container; host publishing remains loopback-only. The
container is healthy on `127.0.0.1:18081`; UI/readiness/writable endpoints return
HTTP 200, and a Windows PowerShell HTTP request returned 200. The mounted DB and
blob paths are writable as UID 200; the default blob store has 3,373 files
(178.9 MiB). No blob-store read-only warnings were found in the container logs.

**Still blocked:** repositories/users/roles API requests return 401. The known
private admin/reader/publisher credential files and environment variables are
absent, so authenticated inventory, artifact-coordinate checks and Maven access
cannot yet be verified. Startup logs identify the stored Maven repository names,
but that is not a substitute for authenticated inventory. No Docker writes to
existing artifacts have been attempted. The temporary container remains on
18081; final cutover to 8081 has not occurred and awaits explicit approval.
Native `/var/lib/nexus` and the verified backup remain intact; the native systemd
service is stopped. To roll back now, stop the Compose container and start the
native service. Do not remove the backup or Docker volume.

## Docker migration implementation checkpoint — 2026-11-17

**Implemented in the checkout:** `nexus/docker-compose.yml` pins Sonatype's
verified `sonatype/nexus3:3.98.1` release tag, uses the image's default
non-root UID 200, stores state in `buy02-nexus-data`, publishes only on
`127.0.0.1`, and checks read/write readiness. The pinned payload corresponds to
the existing 3.98.1-01 native installation. README, runbook and script guide
now describe Compose as the recommended deployment and the native installation
as rollback/fallback.

**Read-only inspection completed 2026-11-17:** Docker 29.7.1 and Compose 5.4.0
are available; the daemon is accessible with approved escalation. No Nexus
container or `buy02-nexus-data` volume exists. The only other volumes are an
empty anonymous volume and `backend_mongo_data`. Compose validation passes.
Native `nexus.service` is active as `nexus:nexus` (PID 291), configured for
`/opt/nexus` and `/var/lib/nexus`, with a loopback listener on 127.0.0.1:8081.
The 3.98.1-01 data directory is 193 MiB, contains the H2 database, `default`
blob store and 3,373 blob files; a read-only scan found no recent blob-store
read-only warning. Read/write readiness endpoints return HTTP 200.

Repositories/users/roles could not be inventoried through the REST API because
the read-only endpoints return 401. The initial admin password file and the
known private credential files are absent; `nexus/env.example` contains blank
examples. Secret values were not read or printed. Artifact file data exists,
but component coordinates/counts cannot be established without authenticated
access. No consistent backup was created: that requires stopping the active
service, which still needs explicit approval. No service, data or Docker state
was changed. Windows access, restored-container checks, Maven publishing,
artifact checksum retrieval, caching and RBAC remain pending.

Sonatype documents that the container writes `/nexus-data` as UID 200 and that
the official image supports the 3.98.1 tag. Data compatibility remains a risk
until a verified offline copy starts successfully; keep the old installation
and the backup intact for rollback. See the [runbook migration procedure](NEXUS_MAVEN_RUNBOOK.md#recommended-deployment-sonatype-docker-compose).

Verification date: 2026-11-16. Branch: `feature/nexus-maven`.
This follows the original [verification report](NEXUS_VERIFICATION.md).
The latest scope preserves Java, Spring Boot, all service POM compatibility
settings, application code, Dockerfiles and CI configuration exactly as received.
No commit, push, merge or privileged installation was performed by this agent.
The newest checkpoint below supersedes historical installation status entries.

## Credential handoff retry — no authenticated changes performed

After the operator reported successful credential setup, the agent checked the
expected file in both the sandbox and the actual WSL host environment. The file
`/tmp/buy02-nexus-completion/credentials.json` was absent in both. Only helper
script metadata was inspected; no secret contents were printed. Running
`python3 /tmp/buy02-nexus-completion/with-credentials.py provision` returned exit 1:
`BLOCKED: private credentials have not been configured.` This occurred before
any API mutation, so no repositories, accounts or artifacts changed.

Fresh read-only checks again passed: Nexus active as nexus:nexus (PID 32859),
IPv4 `127.0.0.1:8081`, both health endpoints, and Windows PowerShell HTTP 200.
The previously completed 446 application tests and 50 tooling tests were not
rerun merely for this credential handoff. No new build or publishing success is
claimed. Provisioning, publication/checksums, proxy caching, version retrieval
and live RBAC remain blocked until the private file is actually available.

Required action: rerun the private credential helper in the same WSL host, or
provide only the alternative saved path/non-secret error if setup was performed
elsewhere. Never send passwords or credential-file contents through chat.

## Current execution after Windows access fix — 2026-11-16

This is the current status and supersedes older checkpoints below. The operator
installed the approved IPv4 override and restarted Nexus. The agent verified
its effects with read-only checks; no sudo, restart or privileged change was
performed in this execution.

### Live Nexus checks

- **PASS:** Windows PowerShell `curl.exe` reached `http://127.0.0.1:8081/` with
  HTTP 200. This is an actual Windows request, not only a WSL curl result.
- **PASS:** IPv4 listener is `127.0.0.1:8081`; service active/running, PID 32859,
  owned by nexus:nexus. No public or wildcard listener was configured.
- **PASS:** UI, `/service/rest/v1/status`, and `/service/rest/v1/status/writable`
  returned HTTP 200.
- **PASS:** namespace root is rw, `/opt` and `/var` are ro, `/var/lib/nexus` is rw.
  The earlier blob-store fix remains effective, with `ProtectSystem=full` and
  explicit protected directories.
- **PASS for observed period:** zero default-blob-store read-only warnings across
  492 entries from invocation `7d2b41d1d4c046bdad67eabaed2bdcef`, observed through
  2026-11-16 19:32:36 UTC. Service readiness began at 19:28:12 UTC.
- **BLOCKED:** full blob write/read proof requires an authenticated artifact upload
  and checksum-verified download. Neither HTTP readiness nor writable mounts
  alone prove this. Java's in-namespace FileStore probe has not been rerun by the
  agent because additional privileged execution is not authorized.
- **PASS:** unauthenticated repositories and blobstores API requests return 401.
  Actual repository policies and reader/publisher permissions remain unverified.

Installed override `/etc/systemd/system/nexus.service.d/20-ipv4-loopback.conf`:

```ini
[Service]
# Use an IPv4 loopback socket that WSL localhost forwarding detects.
Environment="JAVA_TOOL_OPTIONS=-Djava.net.preferIPv4Stack=true"
```

This is the operator-approved Nexus-only networking option. It does not change
the installed Java version, application POMs or application runtime settings.
Nexus uses IPv4 outbound sockets too, so IPv6-only upstreams are not supported
with this option. Before this change, Windows testing showed that NAT forwarding
worked for an IPv4 listener and failed for an IPv4-mapped IPv6 listener. An
isolated Java IPv4 probe succeeded from Windows before the operator applied it.
No `.wslconfig`, portproxy, firewall or public binding change was needed.

### Repository tooling safety correction

The existing `scripts/nexus/manage.py verify-access` used a fixed probe coordinate
and attempted DELETE. It now creates a unique `nexus-access-probe-<uuid>` coordinate
for each denied reader PUT and sends **no DELETE requests**. Unexpected successful
reader writes fail verification and leave only the newly named probe for review;
no automatic cleanup/deletion is attempted. Publisher user-administration denial
and anonymous/reader/publisher access checks remain. Delete privilege absence is
checked against live roles by `verify-config`, not claimed as a runtime DELETE test.

A regression test covers unique probe coordinates and absence of DELETE requests.
**50 tooling tests passed**, zero failures/errors/skips, in 2.159 seconds. This
includes all original 29 tooling tests, the 20 download tests, and the new safety
test. Shell syntax, Python syntax and local POM/settings audit also passed.
The runbook and Darija script guide were updated to describe the changed checks.

### Application verification

**PASS: all six fresh Maven baseline builds completed; 446 tests passed, zero
failures, errors or skips.** All six executable JARs were produced using the
unchanged Java 21.0.13.0.3 runtime and Maven 3.8.7. Existing project Java targets
and Spring Boot versions were preserved. The order-service integration tests
ran with Testcontainers; no tests were disabled.

| Service | Tests | Local JAR |
| --- | ---: | --- |
| discovery | 2 | discovery-0.0.1-SNAPSHOT.jar |
| gateway | 27 | gateway-0.0.1-SNAPSHOT.jar |
| user-service | 48 | user-service-0.0.1-SNAPSHOT.jar |
| product-service | 93 | product-service-0.0.1-SNAPSHOT.jar |
| media-service | 45 | media-0.0.1-SNAPSHOT.jar |
| order-service | 231 | order-service-0.0.1-SNAPSHOT.jar |

Each build used:

```bash
mvn -B -o -ntp -Dmaven.repo.local=/tmp/buy02-nexus-verification/repository -f SERVICE/pom.xml clean verify
```

These offline baseline builds do not prove Nexus dependency resolution. Local
JAR SHA-256 values are recorded in `local-artifact-manifest.json`; no comparison
to a hosted artifact is claimed without an actual upload and download.

### Authentication-dependent work

Administrator, reader and publisher credentials are absent from the agent's
environment and `/tmp/buy02-nexus-completion/credentials.json` is absent. The
existing provision command was attempted through the private credential adapter;
it stopped before network mutations with `BLOCKED: private credentials have not
been configured.`

**Published artifacts this execution: NONE.** Provisioning/reconciliation of
`maven-releases`, `maven-snapshots`, `maven-central`, `maven-public`, account/role
setup, publishing all six snapshots, downloaded checksums, dependency caching,
version retrieval and live RBAC remain **BLOCKED on private credentials**.
No release overwrite or application version change was attempted.

Exact operator action, in a private interactive WSL terminal after completing the
first-login wizard and changing the administrator password:

```bash
python3 /tmp/buy02-nexus-completion/configure-credentials.py
```

The helper uses hidden password prompts, saves only to a mode-0600 file outside
Git inside a mode-0700 directory, and refuses to overwrite an existing file.
Use current passwords for existing service accounts; choose 16+ characters for
new reader/publisher accounts. Tell the agent when ready; never share the JSON
or passwords in chat. No further restart is needed for credential setup.

Once ready, the existing provisioning plan is reviewed before `provision --apply`.
Then `verify-config`, `publish all`, `verify-artifact`, `cache`, `resolve` and the
now non-deleting `verify-access` can run. Publish performs tests and checks hosted,
group and local JAR/POM SHA-256. Multiple timestamped snapshot retrieval can
illustrate versioning without editing any POM or overwriting stable releases.
These are pending actions, not reported successes.

### Evidence and teammate handoff

Evidence is under `/tmp/buy02-nexus-post-ipv4/`: `live-status.json`,
`config-audit.log`, `tooling-tests-final.log`, per-service baseline logs,
`build-results.json`, `maven-version.log`, `local-artifact-manifest.json` and
`before.json` (source hashes).
The unchanged Maven endpoints are:

- `${NEXUS_URL}/repository/maven-public/` — resolution, server ID `nexus-public`.
- `${NEXUS_URL}/repository/maven-releases/` — immutable releases, `nexus-releases`.
- `${NEXUS_URL}/repository/maven-snapshots/` — snapshots, `nexus-snapshots`.
- `${NEXUS_URL}/repository/maven-central/` — Central proxy, a member of the group.

CI needs `NEXUS_URL`, `NEXUS_READ_USERNAME`, `NEXUS_READ_PASSWORD`,
`NEXUS_PUBLISH_USERNAME`, `NEXUS_PUBLISH_PASSWORD`; never administrator credentials.
Use `nexus/maven/settings.xml` and `python3 scripts/nexus/manage.py publish all`,
with existing Java/Maven and Docker available for integration tests. A remote or
container runner needs a private HTTPS endpoint or a deliberate tunnel; its own
localhost does not point to this WSL instance. Live CI publishing integration is
pending authenticated local verification. No CI/Docker/application/POM changes,
commit, push or merge were performed.

## Previous execution — approved blob-store fix installed by operator

Date: 2026-11-16. This section supersedes all earlier status checkpoints below.

### Actual installation and repair status

**Nexus 3.98.1-01 is installed and running on the existing WSL2 systemd host.**
The exact approved drop-in contents and unchanged diagnostic SHA-256 hashes were
verified before attempting installation. The agent's authorized command:

```bash
sudo -n install -D -o root -g root -m 0644 /tmp/nexus-blobstore-fix/10-filestore.conf /etc/systemd/system/nexus.service.d/10-filestore.conf
```

returned `sudo: a password is required` (exit 1). No privileged command was
retried. The operator received one command block for installation, daemon-reload,
restart and the reviewed diagnostic. After the operator's continuation, independent
read-only checks found the exact override installed and effective, a new JVM PID
28343, and a new service invocation `02a199e6e2384bc29825bb9796eb6e88`.
Installation/reload/restart therefore took effect outside the agent's execution;
the agent did not run those commands successfully or alter storage permissions.

| Live check | Actual result |
| --- | --- |
| Effective systemd setting | PASS: `ProtectSystem=full`, explicit read-only paths and existing data write exception |
| Non-root execution | PASS: service User/Group nexus; PID 28343 is a nexus:nexus Java process |
| Service | PASS: active/running; ActiveEnterTimestamp 2026-11-16 18:38:52 UTC |
| Namespace mounts | PASS: `/` rw, `/opt` ro, `/var` ro, `/var/lib/nexus` rw |
| Repeated blob warning after restart | PASS for observed window: 0 matching warnings across 477 current-invocation journal entries through 18:43:06 UTC, more than four minutes after readiness |
| Java `FileStore.isReadOnly=false` inside namespace | BLOCKED: awaiting output from the operator's approved diagnostic; no new privileged execution attempted |
| Local UI and both readiness endpoints | PASS: HTTP 200 |
| Listener exposure | PASS: localhost only, `[::ffff:127.0.0.1]:8081` |
| Unauthenticated repository/admin API access | PASS: HTTP 401 for all four repository roots, repositories API and blobstores API |
| Actual blob write / artifact upload | BLOCKED: no authenticated credentials available |

The absence of warnings and corrected mounts are evidence of the namespace fix,
but HTTP readiness alone does not prove successful blob writes. Full end-to-end
success remains unclaimed until an actual authenticated upload/download and the
Java probe complete. Earlier warnings belong to the previous invocation.

### Tests and packaging actually executed in this completion attempt

All six Maven `clean verify` executions finished with exit 0. **446 tests passed;
zero failures, errors or skips.** These builds used the existing isolated local
cache in offline mode, so they are baseline application verification, not proof
of resolution through Nexus.

| Service | Tests | Failures / errors / skips | Local artifact built |
| --- | ---: | --- | --- |
| discovery | 2 | 0 / 0 / 0 | discovery-0.0.1-SNAPSHOT.jar |
| gateway | 27 | 0 / 0 / 0 | gateway-0.0.1-SNAPSHOT.jar |
| user-service | 48 | 0 / 0 / 0 | user-service-0.0.1-SNAPSHOT.jar |
| product-service | 93 | 0 / 0 / 0 | product-service-0.0.1-SNAPSHOT.jar |
| media-service | 45 | 0 / 0 / 0 | media-0.0.1-SNAPSHOT.jar |
| order-service | 231 | 0 / 0 / 0 | order-service-0.0.1-SNAPSHOT.jar |

**49 Nexus tooling tests passed** (the original 29 plus 20 download tests),
zero failures/errors/skips, 2.280 seconds. Bash syntax and local POM/settings
configuration audit passed. Every application class in the six executable JARs
has classfile major version 61 (Java 17 target). The unchanged host runtime is
Java 21.0.13.0.3 with Maven 3.8.7. No Java or Spring Boot version, POM, application
source, Dockerfile or CI file was modified. Java 11 compliance is not claimed.
The complete application suite includes the existing order-service integration
and Testcontainers tests; none were skipped.

Actual verification commands:

```bash
for service in discovery gateway user-service product-service media-service order-service; do
  mvn -B -o -ntp -Dmaven.repo.local=/tmp/buy02-nexus-verification/repository -f "$service/pom.xml" clean verify
done
python3 -m unittest discover -s scripts/nexus -p 'test_*.py' -v
bash -n nexus/install.sh nexus/download.sh nexus/healthcheck.sh
python3 scripts/nexus/manage.py audit
systemctl show nexus.service -p User -p Group -p MainPID -p ActiveState -p SubState -p ProtectSystem -p ReadOnlyPaths -p ReadWritePaths
findmnt -N 28343 -T / -o TARGET,SOURCE,FSTYPE,OPTIONS
findmnt -N 28343 -T /opt -o TARGET,SOURCE,FSTYPE,OPTIONS
findmnt -N 28343 -T /var -o TARGET,SOURCE,FSTYPE,OPTIONS
findmnt -N 28343 -T /var/lib/nexus -o TARGET,SOURCE,FSTYPE,OPTIONS
ps -p 28343 -o user,group,pid,comm
ss -ltn 'sport = :8081'
journalctl --no-pager -o json _SYSTEMD_INVOCATION_ID=02a199e6e2384bc29825bb9796eb6e88
```

The build loop was executed through a temporary Python runner that records each
exit and parses the actual Surefire/Failsafe XML reports. Read-only HTTP checks
used Python urllib and recorded status codes without response bodies. Test runs
used normal-user host access for Docker and local TLS fixture sockets, never sudo.
Evidence under `/tmp/buy02-nexus-completion/`: `build-results.json`, six
`*-baseline.log` files, `tooling-tests.log`, `config-audit.log`, `maven-version.log`,
`local-artifact-manifest.json` (local JAR SHA-256 values), `anonymous-http.json`,
`service-status.log`, `listener-status.log`, `post-fix-observation.json` and
`before.json` (source hashes). Generated JARs are local build outputs, not uploads.

### Repository, publication, caching and security status

**Published artifacts in this execution: NONE.** No publication, proxy-cache
fill, authenticated retrieval or account creation is claimed. Administrator,
reader and publisher credentials were absent from the environment; the private
credential file was also absent. The existing provisioning workflow was invoked
through the credential adapter and stopped before network changes with
`BLOCKED: private credentials have not been configured.`

| Repository | Intended policy | Live provisioning status |
| --- | --- | --- |
| maven-releases | Maven hosted, RELEASE, ALLOW_ONCE | BLOCKED on credentials; unauthenticated HTTP 401 does not prove configuration |
| maven-snapshots | Maven hosted, SNAPSHOT, ALLOW | BLOCKED on credentials |
| maven-central | Maven proxy, https://repo.maven.apache.org/maven2/ | BLOCKED on credentials |
| maven-public | Group: releases, snapshots, central | BLOCKED on credentials |

Least-privilege reader/publisher role definitions, credential placeholders,
mirror/deployment IDs, release immutability checks and checksum verification are
covered by passing local tests. Actual user roles, password validity, reader write
denial, publisher upload permission and publisher administration denial remain
BLOCKED pending authenticated checks. Authentication has not been disabled;
anonymous requests were actually rejected. No repositories were deleted,
recreated or changed by this attempt, and no stored artifacts were overwritten.

Maven dependency resolution through Nexus, cached proxy assets, snapshot
publication/retrieval and multiple timestamped snapshot retrieval remain BLOCKED
on credentials. Application versions stay at `0.0.1-SNAPSHOT`. Stable releases
were not attempted under the no-POM-change rule; existing tooling supports their
immutable deployment when a separately authorized version is already selected.

### Exact remaining operator steps and continuation

1. The systemd fix is already effective; do not reinstall or repeat its restart.
   Return only the read-only diagnostic output from the already supplied local
   command block, including both Java probe results. Never include passwords.
2. Complete the first-login wizard locally at `http://127.0.0.1:8081` if still
   pending, change the initial administrator password and keep anonymous access
   disabled. No credential retrieval via additional sudo is authorized here.
3. In a private interactive WSL terminal run
   `python3 /tmp/buy02-nexus-completion/configure-credentials.py`.
   This temporary helper prompts with getpass (no echo), and writes only
   `/tmp/buy02-nexus-completion/credentials.json` with mode 0600 inside the 0700
   directory. It refuses to overwrite an existing file. Use current credentials
   for existing accounts; new reader/publisher passwords need 16+ characters.
   The helper never prints secrets or embeds them in process arguments. Shell
   exports in another terminal alone do not populate the agent's environment.
   Tell the agent when it finishes; do not paste the file or passwords into chat.

Once credentials are available, the prepared temporary adapter runs the EXISTING
project tooling with private environment variables and strips administrator
credentials from build/publish subprocesses:

```bash
python3 /tmp/buy02-nexus-completion/with-credentials.py provision
python3 /tmp/buy02-nexus-completion/with-credentials.py provision --apply
python3 /tmp/buy02-nexus-completion/with-credentials.py verify-config
python3 /tmp/buy02-nexus-completion/with-credentials.py publish all
python3 /tmp/buy02-nexus-completion/with-credentials.py cache
```

These commands are pending, not successful results. Publication runs tests before
deploying and verifies hosted/group/local JAR and POM SHA-256 for every service.
The dedicated `/tmp/buy02-nexus-completion/maven-cache` avoids changing global
settings and permits actual Nexus dependency fetch verification. Snapshot
metadata must be inspected before and after publication to retain and retrieve
previous timestamped versions without POM edits. Runtime access tests must avoid
overwriting or deleting any existing probe/application artifact; the existing
fixed-path `verify-access` destructive probes require review before execution.
No additional sudo is needed for authenticated Nexus REST/Maven operations.
Temporary credential files are outside source control and should be removed
privately when the operator no longer needs this execution environment.

### Teammate's CI integration handoff

- Use a CI-reachable private HTTPS Nexus URL (or an intentional localhost tunnel).
  A remote/container runner's `127.0.0.1` does not refer to this WSL host.
- Repository URLs: `${NEXUS_URL}/repository/maven-public/`,
  `${NEXUS_URL}/repository/maven-releases/`,
  `${NEXUS_URL}/repository/maven-snapshots/`; Maven Central is proxied by
  `maven-central` inside the group.
- Inject only `NEXUS_READ_USERNAME`, `NEXUS_READ_PASSWORD`,
  `NEXUS_PUBLISH_USERNAME`, `NEXUS_PUBLISH_PASSWORD`, plus `NEXUS_URL`.
  Reader uses role `buy02-maven-reader`; publisher uses `buy02-maven-publisher`.
  Do not inject administrator credentials into CI. Maven settings are
  `nexus/maven/settings.xml`; IDs are nexus-public, nexus-releases, nexus-snapshots.
- Keep the existing working Java runtime, Maven and Docker access for existing
  integration tests. `python3 scripts/nexus/manage.py publish all` runs all six
  test/deploy lifecycles and checksum checks; optionally run `build all` first.
  `verify-artifact SERVICE --local` repeats hosted/group/local verification;
  `resolve SERVICE --version 0.0.1-SNAPSHOT` tests retrieval through the mirror.
- Full CI publishing integration remains pending successful local authenticated
  verification. No Docker repositories, images, CI files or pipeline triggers
  were modified. No commit, push or merge was performed.

## Previous checkpoint — blob-store repair prepared before approval

**Current status: Nexus 3.98.1-01 IS INSTALLED and running; blob-store repair is
PREPARED, NOT APPLIED and NOT VERIFIED.** The operator completed installation
and the privileged diagnostic. No privileged change or restart was executed by
the agent during this repair. Older installation-blocked entries below are history.

### Confirmed diagnosis and baseline

The operator reports `nexus:nexus` ownership and 0750 on the data/blob directories,
a writable host filesystem, and these results from the reviewed read-only probe:

| Probe | Outside service namespace | Inside service namespace |
| --- | --- | --- |
| `Files.isWritable` | true | true |
| `FileStore.isReadOnly` | false | true |
| Root mount | writable | read-only |
| `/var/lib/nexus` mount | writable | writable bind mount |

This isolates the failure to filesystem classification in the service mount
namespace, not insufficient disk space or blob ownership. The installed unit
uses `ProtectSystem=strict` with `ReadWritePaths=/var/lib/nexus`. Java's Linux
FileStore lookup can walk past a same-device bind mount to the read-only root.

Agent baseline checks this turn independently confirmed:

- systemd 255 on the existing WSL2 host; installed unit and installer template
  inspected; no pre-existing `nexus.service.d` directory at inspection time.
- `ActiveState=active`, `SubState=running`, `User=nexus`, `Group=nexus`;
  PID 24102 is a nexus-owned Java process.
- UI `http://127.0.0.1:8081/`: HTTP 200. Both readiness endpoints also pass.
- Journal warnings still repeat, including at `2026-11-16 18:28:40 UTC`:
  `File blob store 'default' is not writable. Read only: true.`
  **Readiness success does not establish blob-store writability.**
- Nexus reader/publisher/admin credential environment variables are absent
  (presence only was checked; no values printed).

### Proposed change, not installed

Updated `nexus/systemd/nexus.service` for future fresh installs. The installer
already copies that template; its managed-install early return does not update
an existing unit, so rerunning the installer is not this repair procedure.
No installer or application changes were needed.

```diff
-ProtectSystem=strict
+ProtectSystem=full
+ReadOnlyPaths=/opt /var /mnt /media /srv /run
 ReadWritePaths=/var/lib/nexus
```

A four-line drop-in is staged at `/tmp/nexus-blobstore-fix/10-filestore.conf`:

```ini
[Service]
# Keep Java FileStore detection compatible with the writable data bind mount.
ProtectSystem=full
ReadOnlyPaths=/opt /var /mnt /media /srv /run
```

It inherits the existing data write exception. `ProtectHome`, `PrivateTmp`,
`NoNewPrivileges`, non-root execution and UMask remain enabled. `full` protects
`/usr`, `/boot`, `/efi` and `/etc`; the explicit paths protect application files,
other `/var` content and mounted Windows files. The root mount itself becomes
writable at mount level, but ordinary ownership still prevents nexus from
creating root entries. Unlike `strict`, newly added top-level directories are
not automatically read-only; review the explicit list when adding host paths.
A separate writable filesystem could preserve `strict` but requires storage
migration. Another bind mount of the same filesystem does not address the
observed Java detection behavior. Neither alternative was executed.

### Verification actually executed

| Check | Status / evidence |
| --- | --- |
| Existing Nexus tooling tests | PASS: original 29 plus 20 download tests; 49 total, 0 failures/errors/skips, 1.750 seconds |
| Shell syntax | PASS: install.sh, download.sh and healthcheck.sh |
| Local Maven configuration audit | PASS: all six POMs/settings, coordinates, IDs and mirror |
| systemd configuration parsing | PASS on isolated copy using `/usr/bin/true` for ExecStart; real binary is inaccessible to the normal user, so direct executable validation was blocked |
| Non-root execution, UI and readiness before repair | PASS; does not demonstrate corrected blob storage |
| Post-change namespace probe and warning observation | BLOCKED pending explicit approval, apply and restart |
| Real artifact upload/download and checksum | BLOCKED: repair pending and credentials unavailable |
| Application tests | NOT RERUN for this service-template-only change; earlier 446 passing tests remain historical |

Commands executed without sudo included:

```bash
systemctl show nexus.service -p User -p Group -p MainPID -p ActiveState -p SubState -p FragmentPath -p WorkingDirectory -p ProtectSystem -p ReadWritePaths -p ReadOnlyPaths
journalctl -u nexus.service --no-pager -n 40 -o cat
ps -p 24102 -o user,group,pid,comm
bash nexus/healthcheck.sh
curl --noproxy '*' --silent --show-error --max-time 5 -o /dev/null -w 'UI HTTP %{http_code}\n' http://127.0.0.1:8081/
bash -n nexus/install.sh nexus/download.sh nexus/healthcheck.sh
python3 scripts/nexus/manage.py audit
python3 -m unittest discover -s scripts/nexus -p 'test_*.py' -v
systemd-analyze verify /tmp/nexus-blobstore-fix/config-check/nexus.service
```

Evidence: `/tmp/nexus-blobstore-fix/tooling-tests.log`, `unit-validation.log`,
and `before.json` (repository file hashes captured before edits).
The validation copy was never installed or started. No repositories, artifacts,
permissions or Nexus data were changed.

### Approval-gated next steps

After explicit approval and rechecking that the destination drop-in is absent:

```bash
sudo -n install -D -o root -g root -m 0644 /tmp/nexus-blobstore-fix/10-filestore.conf /etc/systemd/system/nexus.service.d/10-filestore.conf
sudo -n systemctl daemon-reload
sudo -n systemctl restart nexus.service
sudo -n bash /tmp/nexus-blobstore-diagnosis/inspect.sh
```

The first command creates only the root-owned override and its directory; the
second reloads unit definitions; the third briefly interrupts Nexus to create
its new mount namespace; the fourth repeats the unchanged read-only diagnostic.
If noninteractive sudo is unavailable, run the approved commands in a private
local terminal without `-n`; never put a password in chat or command arguments.
The prepared `/tmp` files must be reviewed/recreated if removed by reboot.

Require the namespace probe to return `FileStore.isReadOnly=false` and
`Files.isWritable=true`; confirm `/opt` and `/var` remain read-only while the
nested data mount remains writable. Check service owner, localhost binding,
HTTP readiness and journal entries from the new service invocation, observing
at least 60 seconds after startup (the old warning repeated about every 15s).
Old journal warnings are historical and must not be mistaken for a new failure.
Then use the existing `publish gateway` and `verify-artifact gateway --local`
commands with private reader/publisher environment variables. The latter compares
the downloaded hosted JAR/POM SHA-256 with local files. Do not claim success
before these checks pass. CI/CD integration stays pending this live verification;
its Maven commands, repository URLs and least-privilege credentials remain as
specified in the existing runbook. No CI or Docker changes are needed.

## Download reset repair — historical execution

The operator reported a curl 56 connection reset at roughly 482 MB/500 MB,
followed by `Unit nexus.service could not be found`. Inspection confirms that
the original installer downloaded to `$work/nexus-3.98.1-01-linux-x86_64.tar.gz`,
where `work=$(mktemp -d)`, with curl `--retry 3` but no resume option. The EXIT
trap removed that entire directory on failure. Service installation occurs later,
so a missing unit after that download failure is expected.

**Actual installation status: NOT INSTALLED / NOT VERIFIED.** Current read-only
host checks show `LoadState=not-found`, `ActiveState=inactive`, no port 8081
listener and curl exit 7 / HTTP 000. A pre-existing non-root nexus account now
exists (uid 997, non-login shell), consistent with the old installer creating it
before downloading. It was preserved. No sudo was executed for this repair.

The workflow is now corrected:

- Added `nexus/download.sh`, called by the existing installer. Downloads persist
  under `/var/cache/nexus/downloads`; extraction scratch cleanup never removes
  them or Nexus data.
- Every attempt uses curl `--continue-at -`; five attempts use 2/4/8/16-second
  backoff, a 20-second connect timeout, a 1800-second transfer timeout and a
  60-second low-speed timeout. Curl 56/18/28 and transient failures can resume
  the bytes already received.
- Partial metadata binds the expected URL and checksum; a complete verified
  cache entry is reused unchanged. Range refusal preserves only the incomplete
  candidate and restarts its download. Stale/corrupt candidates are retained
  under unique `.rejected.*` names, never extracted.
- The unchanged pinned SHA-256 is mandatory before a candidate becomes the final
  archive, and is checked again in install.sh immediately before extraction.
- Optional `NEXUS_PARTIAL_ARCHIVE` imports a surviving legacy partial by copying
  it; its original is retained. The old EXIT trap normally deleted the failed
  partial, so unavailable bytes are not claimed recovered.
- Existing installation/data guards and managed-install reuse remain intact.
  Account creation moved after verified extraction. Download-stage retries are
  automatic; interrupted installation paths beyond that stage are preserved
  and require review instead of destructive replacement.

The exact URL is
`https://download.sonatype.com/nexus/3/nexus-3.98.1-01-linux-x86_64.tar.gz`.
The final cache archive is
`/var/cache/nexus/downloads/nexus-3.98.1-01-linux-x86_64.tar.gz`, with `.part`,
`.source` and `.lock` siblings. The pinned checksum remains
`a8b204c50708729492380697c1d64f342281468ddfd96e1ab199de86a478e768`.

### Tests executed for this repair

| Check | Actual result |
| --- | --- |
| Bash syntax for installer, downloader and healthcheck | PASS |
| Python syntax for the added regression tests | PASS |
| Existing Nexus tooling tests | PASS: all 29 unchanged tests |
| New download tests | PASS: 20 tests using real curl and a local trusted HTTPS fixture |
| Combined suite | PASS: 49 tests, 0 failures/errors/skips, 3.394 seconds |
| Real pinned Nexus archive download | NOT EXECUTED in this repair; no full vendor archive is claimed verified |
| Nexus startup/non-root process/localhost health | BLOCKED until approved installation succeeds |
| Application/POM/Java/Spring/Docker/CI preservation | Verified by hashes against the initial repair snapshot |

The new tests cover actual HTTP Range resume, connection resets, the reported
curl 56 result, unsupported/ignored Range, HTTP 416, corrupt bytes/wrong checksum,
complete-cache reuse, changed/missing metadata, legacy import, concurrent locks,
symlink refusal, retry exhaustion and a subsequent successful resumed invocation.
The first sandbox run passed the original 29 tests but could not create a
fixture socket (`PermissionError`). The full suite was then run **as uid 1000,
without sudo**, outside that socket restriction and passed. No TLS validation
was disabled. The 446 application tests were not rerun for this downloader-only
repair; their earlier results remain historical evidence.

```bash
bash -n nexus/install.sh nexus/download.sh nexus/healthcheck.sh
python3 -m py_compile scripts/nexus/test_download.py
python3 -m unittest discover -s scripts/nexus -p 'test_*.py' -v
```

Logs: `/tmp/buy02-nexus-download-fix/tests-final.log` (passing final suite) and
`tests.log` (initial sandbox restriction). The Darija guide and installation
runbook now explain the changed workflow and both added files.

### Exact retry and post-install verification

Only after approving the privileged action, run locally from the repository root:

```bash
sudo bash nexus/install.sh
```

This creates the protected download cache, resumes/verifies the archive, and
only then installs the dedicated account, application, persistent storage,
healthcheck and systemd units. It does not change the application JDK or Spring
Boot. If a legacy partial actually survived, use the explicit import command in
the runbook. A missing/deleted old partial starts a new persistent download.

After the installer reports success, use these non-sudo checks:

```bash
bash nexus/healthcheck.sh
systemctl show nexus.service -p User -p Group -p MainPID -p ActiveState
ps -u nexus -o user,pid,args
curl --fail --location --show-error --silent -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:8081/
```

Require `ActiveState=active`, service User/Group nexus, an actual nexus-owned JVM,
successful read/write readiness and an accessible localhost UI. These runtime
checks have not passed yet; no installation, repository creation, publication,
cache behavior or live RBAC success is claimed. Existing CI handoff instructions
below still apply after the live checks succeed.

## Earlier installation execution checkpoint (before the reported reset)

The latest request requires explicit approval **before every sudo command** and
prohibits all POM changes, including application version changes. The exact
installer command `sudo -n bash nexus/install.sh` and its account, filesystem,
systemd and startup effects have been presented for approval. It has **not been
executed** while that approval is pending. No sudo command was used during the
current read-only inspection.

Fresh host checks confirm Ubuntu 24.04.4 under WSL2, x86-64, systemd running,
port 8081 unoccupied, approximately 924 GB free on the Linux filesystem, and all
installer dependencies present. Neither the nexus account/group nor installation
paths/service exist. The configured Nexus URL refuses connections. All Nexus
credential variables are absent; their values were never printed.

The existing host now reports Java 21.0.13.0.3. That is the runtime already
installed when this execution began; this work did not upgrade or change it.
Current execution logs are under `/tmp/buy02-nexus-live/`. The 29 tooling tests,
local configuration audit and Bash syntax check have passed again. Application
builds have now also finished: **446 tests passed, zero failures/errors/skips**,
and all six executable JARs were produced. All six effective POMs and the Maven
settings parser passed again. These were baseline builds against the isolated
local Maven cache, not authenticated Nexus builds.

### Commands and system changes in the current execution

The commands actually executed included `uname -a`, `cat /etc/os-release`, `id`,
`df -h /opt /var/lib /tmp`, `free -h`, dependency `command -v` checks, read-only
inspection of the existing installer and invoked scripts/units, `getent passwd
nexus`, `getent group nexus`, `ss -ltnp 'sport = :8081'`, `systemctl
is-system-running`, `systemctl show nexus.service -p LoadState -p ActiveState`,
`docker info`, a localhost readiness curl request, the 29 tooling tests, audit,
syntax checks, the six baseline Maven builds, and the six effective-pom goals.

The six baseline builds used:

```bash
for service in discovery gateway user-service product-service media-service order-service; do
  mvn -B -o -ntp \
    -Dmaven.repo.local=/tmp/buy02-nexus-verification/repository \
    -f "$service/pom.xml" clean verify
done
```

**Actual Nexus installation status: NOT INSTALLED / BLOCKED on approval.**
No sudo command has been executed in this attempt. No Nexus system account,
installation path, persistent storage, service unit, repository, role or
published artifact has been created. The builds used temporary Testcontainers
resources for the existing MongoDB integration tests; no Dockerfiles or CI
configuration were changed. Local build outputs and execution logs were produced.

**Repositories created: none in this session. Published artifacts: none.**
The repository files describe the intended four repositories; they are not proof
of provisioned repositories. Live health, authenticated repository access,
snapshot publishing/download, caching and RBAC checks remain BLOCKED until
installation approval, a healthy instance and private credentials are available.

The pending command is `sudo -n bash nexus/install.sh`. It creates the nexus
account/group, installs the pinned release under /opt, creates protected data
under /var/lib/nexus, installs the healthcheck/systemd units and starts the
localhost-only service. If non-interactive sudo authentication is unavailable,
it will stop without asking for a password through this session; the operator
must run the approved installer in a private local terminal instead.

## 1. Fully completed and verified

| Step | Status | Actual evidence |
| --- | --- | --- |
| Detect installation environment | PASS | Ubuntu 24.04.4, Linux x86-64 under WSL2. Host systemd reports running outside the restricted shell; Docker server is 29.7.1. |
| Inspect existing installer | PASS | Reviewed nexus/install.sh, its JVM/storage handling, service units, user/permission setup, fresh-install guards and healthcheck before any installation attempt. It targets a Linux x86-64 systemd host, which matches this WSL host outside the sandbox. |
| Preserve all service configurations and source | PASS | Compared SHA-256 hashes against the initial follow-up snapshot. All six POMs, application files, scripts, Dockerfiles and CI files remain unchanged. Only documentation is added/updated in this follow-up. |
| discovery clean verify | PASS | 2 tests, no failures/errors/skips; executable JAR produced. |
| gateway clean verify | PASS | 27 tests, no failures/errors/skips; executable JAR produced. |
| user-service clean verify | PASS | 48 tests, no failures/errors/skips; executable JAR produced. |
| product-service clean verify | PASS | 93 tests, no failures/errors/skips; executable JAR produced. |
| media-service clean verify | PASS | 45 tests, no failures/errors/skips; executable JAR produced. |
| order-service clean verify | PASS | 231 tests, no failures/errors/skips, including actual MongoDB Testcontainers tests; executable JAR produced. |
| Existing Nexus tooling tests | PASS | All 29 existing tests passed again, without editing the tests or scripts. |
| Local Maven/Nexus configuration audit | PASS | manage.py audit parsed all six POMs/settings and validated coordinates, deployment IDs and mirror configuration. |
| Effective Maven POMs | PASS | All six effective-pom goals passed again; resolved hosted URLs and deployment credential IDs were checked in the generated models. |
| Maven settings parser | PASS | Offline validate with the tracked settings and the existing temporary parent-free POM passed again. This is syntax/model validation, not a live mirror connection. |
| Existing Java baseline | PASS | Rebuilt all services using existing Java 21, preserved compiler target 17 and verified application class major version 61 in all six JARs. |
| Script syntax | PASS | bash -n nexus/install.sh nexus/healthcheck.sh. |
| systemd unit syntax | PASS with limitation | Temporary unit copies using /usr/bin/true in place of uninstalled executables passed systemd-analyze verify. Real service execution is BLOCKED. |
| Darija documentation | PASS | NEXUS_SCRIPTS_EXPLAINED.md explains every existing script, its commands, internals, use, failures and verification in Moroccan Darija with Arabic script. |

**446 application tests and 29 tooling tests passed again.** The application
builds used the existing Maven 3.8.7 and isolated cache, resolving offline from
previously downloaded dependencies. These builds do not demonstrate Nexus access.

Exact commands used:

```bash
for service in discovery gateway user-service product-service media-service order-service; do
  mvn -B -o -ntp \
    -Dmaven.repo.local=/tmp/buy02-nexus-verification/repository \
    -f "$service/pom.xml" clean verify
done
python3 -m unittest discover -s scripts/nexus -p 'test_*.py' -v
python3 scripts/nexus/manage.py audit
bash -n nexus/install.sh nexus/healthcheck.sh
```

Each service's effective model was also generated with:

```bash
NEXUS_URL=http://127.0.0.1:8081 mvn -B -o -ntp \
  -Dmaven.repo.local=/tmp/buy02-nexus-verification/repository \
  -f gateway/pom.xml \
  org.apache.maven.plugins:maven-help-plugin:3.4.0:effective-pom \
  -Doutput=/tmp/buy02-nexus-followup/gateway-effective-pom.xml
```

The same command was run for the other five service POMs. Effective-model logs
are `/tmp/buy02-nexus-followup/SERVICE-effective.log`.

Application test logs are in `/tmp/buy02-nexus-followup/SERVICE.log`; tooling
results are in `tooling-tests.log`. `results.json` records counts, built JAR paths
and their SHA-256 values. These files contain local verification evidence, not
claimed Nexus publications.

## 2. Work prepared but not executed

The existing implementation is retained, including:

- The pinned native installer, nexus service account, protected persistent
  `/var/lib/nexus` storage, localhost listener, startup/restart and health checks.
- Four repository definitions: immutable maven-releases, writable snapshots,
  Maven Central HTTPS proxy and the maven-public group.
- Supported REST provisioning, restricted reader/publisher roles, separate users,
  disabled anonymous access and environment-based credentials.
- Maven mirror/settings and each service's existing deployment configuration.
- Publishing that runs tests and confirms server-downloaded JAR/POM checksums.
- Proxy/cache, authentication/permission and artifact retrieval verification.

No real repository, account, artifact upload, download or cache behavior is
reported verified without a live server. The 29 unit tests simulate server
responses; they do not replace these live checks.

## 3. Work blocked by permissions or credentials

| Step | Status | Evidence and reason |
| --- | --- | --- |
| Native Nexus installation | BLOCKED | No explicit approval to execute the privileged installer has been received. This session is uid 1000. The earlier sudo check required private authentication; no password is requested in chat. |
| Nexus service availability | BLOCKED | Host reports nexus.service inactive. The localhost readiness probe returned curl exit 7 / HTTP 000. /opt/nexus, /var/lib/nexus and the custom service unit are absent. |
| Verify runtime non-root execution/persistence | BLOCKED | Installation must happen first; source configuration alone is insufficient evidence. |
| Repository and RBAC provisioning | BLOCKED | No live Nexus or NEXUS_URL/admin credentials. No NEXUS_* credential variables were set; only their presence was checked, never their values. |
| Snapshot upload and download | BLOCKED | Requires provisioned Nexus and reader/publisher credentials. No successful publication is claimed. |
| Stable release upload | BLOCKED | Requires live policy verification and a fresh permitted release coordinate before executing. No version was changed to manufacture a release. |
| Maven resolution via Nexus | BLOCKED | Settings are valid locally; a real mirror endpoint and authenticated reader are absent. |
| Dependency cache proof | BLOCKED | Requires live group/proxy requests and cached asset evidence from Nexus. |
| Runtime access-control probes | BLOCKED | Requires active reader/publisher accounts and disabled anonymous access on the real instance. |

The request for explicit installation approval is separate from read-only host
inspection and running the authorized application tests. Neither authorizes
privileged host changes by implication. If approval arrives, an operator may
still need to authenticate privately in their own terminal.

## 4. Java 11 status

**FAIL for compatibility; migration DEFERRED and UNRESOLVED.** The existing
application baseline is preserved and all 446 tests still pass on it. The exact
findings are in [JAVA11_COMPATIBILITY.md](JAVA11_COMPATIBILITY.md). No Java,
Spring Boot or POM compatibility settings were changed. No further migration
work is attempted under the latest instruction.

## 5. Exact remaining manual actions

Run the following only on the intended local WSL/Linux Nexus host, in a private
terminal. Keep credentials out of chat, command history values, screenshots and
shared logs. Application Docker publishing and pipeline configuration remain
the teammate's responsibility.

### A. Approve and execute the reviewed installer

```bash
cd /mnt/c/Users/asana/OneDrive/Desktop/nexus
bash -n nexus/install.sh nexus/healthcheck.sh
# Privileged changes: execute only after approving this local installation.
sudo bash nexus/install.sh
systemctl status nexus --no-pager
bash nexus/healthcheck.sh
ps -eo user,pid,comm
sudo ss -ltnp 'sport = :8081'
sudo stat -c '%U:%G %a %n' /var/lib/nexus /var/lib/nexus/etc/nexus.properties
```

Expect a nexus-owned JVM, persistent data owned by nexus:nexus, directory mode
0750, configuration mode 0640, and a listener only at 127.0.0.1:8081. Retain the
vendor-bundled Nexus JVM; do not change the application's JDK.

If the installer reports an existing path or archive mismatch, stop and inspect
the cause. Do not delete data or weaken guards to force installation. WSL must
remain running for its services to remain available; this does not provision an
always-on external server or configure Windows startup policy.

### B. Complete initial setup and supply credentials privately

Open `http://127.0.0.1:8081/`. Read the generated initial password from
`/var/lib/nexus/admin.password` privately on the host, complete the setup wizard,
change the administrator password and disable anonymous access.

```bash
set +x
export NEXUS_URL=http://127.0.0.1:8081
export NEXUS_ADMIN_USERNAME=admin
export NEXUS_READ_USERNAME=buy02-reader
export NEXUS_PUBLISH_USERNAME=buy02-publisher
read -rp 'Reader account email: ' NEXUS_READ_EMAIL
read -rp 'Publisher account email: ' NEXUS_PUBLISH_EMAIL
export NEXUS_READ_EMAIL NEXUS_PUBLISH_EMAIL
read -rsp 'Changed Nexus administrator password: ' NEXUS_ADMIN_PASSWORD; echo
export NEXUS_ADMIN_PASSWORD
read -rsp 'Reader password (16+ characters for a new account): ' NEXUS_READ_PASSWORD; echo
export NEXUS_READ_PASSWORD
read -rsp 'Publisher password (16+ characters for a new account): ' NEXUS_PUBLISH_PASSWORD; echo
export NEXUS_PUBLISH_PASSWORD
```

For existing accounts, supply their current password; provisioning does not reset
it. These interactive prompts are local actions, not requests to disclose secrets.

### C. Provision and verify configuration

```bash
python3 scripts/nexus/manage.py provision
python3 scripts/nexus/manage.py provision --apply
python3 scripts/nexus/manage.py verify-config
python3 scripts/nexus/manage.py verify-access
python3 scripts/nexus/manage.py cache
```

Inspect the output and require successful exit status for each command before
continuing. Confirm releases use ALLOW_ONCE and policy RELEASE, snapshots use
ALLOW and SNAPSHOT, Central points to HTTPS Maven Central, and the group includes
all three. Roles must match the project definitions without administrator grants.

### D. Build through Nexus, publish and check the snapshot

```bash
# Publishing requires no administrative credential in the build environment.
unset NEXUS_ADMIN_USERNAME NEXUS_ADMIN_PASSWORD
export MAVEN_BIN=/usr/bin/mvn
export NEXUS_MAVEN_CACHE=$(mktemp -d /tmp/buy02-nexus-live.XXXXXX)
python3 scripts/nexus/manage.py build all
python3 scripts/nexus/manage.py publish gateway
python3 scripts/nexus/manage.py verify-artifact gateway --local
python3 scripts/nexus/manage.py resolve gateway --version 0.0.1-SNAPSHOT
```

All service versions remain 0.0.1-SNAPSHOT. Publishing must report confirmed
downloaded JAR/POM checksums. Resolve places the actual application artifact into
the selected local Maven cache; it does not prove that any blocked step already
ran in this session. The fresh cache also makes Maven contact the configured
mirror for dependencies and plugins; inspect logs for nexus-public.

### E. Stable release publication: current scope restriction

All six existing POMs declare `0.0.1-SNAPSHOT`, and the current task prohibits
modifying **any** POM file. Therefore no `set-version` command will be run and
no snapshot binary will be relabeled as a stable release merely to produce a
passing demonstration. Stable publishing remains BLOCKED unless an authentic
stable artifact/configuration is supplied within the authorized scope.

When such an artifact is available, first verify the actual release repository
policy is ALLOW_ONCE and the coordinate is unused. Never weaken the policy or
overwrite an existing artifact. Existing release verification can be run for a
real previously published coordinate with `verify-artifact --version VERSION`
and `resolve --version VERSION`; its existence must be established first.

For the authorized snapshot publication, download the exact timestamped filename
shown by successful `verify-artifact` output. Curl's `--user USERNAME` prompts
privately for the password; do not include the password in the URL or arguments.
Compare the saved file's `sha256sum` with the confirmed server hash.

### F. Capture real evidence and hand off

Record actual test counts, provisioning read-back, permissions, downloaded
checksums and proxy assets/request logs. Use the screenshot checklist in
[NEXUS_MAVEN_RUNBOOK.md](NEXUS_MAVEN_RUNBOOK.md). Report FAIL on an unsuccessful
attempt and BLOCKED for steps whose prerequisite remains unavailable.

Give the teammate the three Maven URLs and group URL, the explicit settings
path, publishing commands and reader/publisher credential variable names.
Do not provide administrator credentials to CI and do not expose Nexus publicly.
