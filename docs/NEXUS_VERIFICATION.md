# Actual Nexus Maven verification

Execution date: **2026-11-16**. Branch: **feature/nexus-maven**.
The repository's pre-existing changes were preserved. A SHA-256 baseline of 428
tracked files was saved before implementation. Only the six service POMs and
README changed from that baseline; new Nexus tooling/documentation was added.
No commit, push, merge or production deployment was performed.

## Application build environment

- Ubuntu 24.04.4 on WSL2, Linux x86-64.
- Installed Maven 3.8.7, build runtime OpenJDK 21.0.12.1, compiler target Java 17.
- Existing wrappers request Maven 3.9.16. These verification builds used the
  installed Maven explicitly; the wrappers themselves were not downloaded/tested.
- An isolated Maven repository was created at
  `/tmp/buy02-nexus-verification/repository`, seeded from the existing cache.
  Missing dependencies were downloaded from Maven Central with elevated network
  access. The global Maven settings were not edited.
- These baseline builds used normal Maven Central resolution, **not Nexus**.
  They verify application preservation, tests and packaging.

The exact build command, run for each service, was:

```bash
mvn -B -Dmaven.repo.local=/tmp/buy02-nexus-verification/repository \
  -f SERVICE/pom.xml clean verify
```

Logs are under `/tmp/buy02-nexus-verification/` on the execution machine. These
temporary logs are local evidence, not committed credentials or portable artifacts.

## Actual results

| Check | Actual result | Evidence/meaning |
| --- | --- | --- |
| discovery clean verify | PASS: 2 tests, 0 failures/errors/skips | Executable JAR produced |
| gateway clean verify | PASS: 27 tests, 0 failures/errors/skips | Executable JAR produced |
| user-service clean verify | PASS: 48 tests, 0 failures/errors/skips | Executable JAR produced |
| product-service clean verify | PASS: 93 tests, 0 failures/errors/skips | Executable JAR produced |
| media-service clean verify | PASS: 45 tests, 0 failures/errors/skips | Executable JAR produced |
| order-service clean verify | PASS: 231 tests, 0 failures/errors/skips | Executable JAR produced; real MongoDB Testcontainers integration tests included |
| Java 11 application compatibility | FAIL: existing application incompatible | Real Temurin 11 builds failed; details below |
| Local XML and coordinate audit | PASS | All six POMs and settings parsed; IDs/mirror match |
| Effective Maven POMs | PASS for all six | Maven resolved the configured release and snapshot URLs |
| Version update workflow | PASS: 1.0.0, 1.0.1 and 1.0.0-SNAPSHOT | Pinned versions plugin changed only the project version on a temporary gateway POM |
| Maven settings parser | PASS | Maven validate with the example settings and a minimal offline verification POM |
| Offline tooling tests | PASS: 29 tests | Security guards, role limits, repository reconciliation, snapshot paths, checksum errors, administrator environment exclusion and health checks |
| Bash syntax | PASS | `bash -n nexus/install.sh nexus/healthcheck.sh` |
| systemd static syntax | PASS with executable placeholders | Real executable paths are not installed here; this does not verify service startup |
| Installer privilege guard | PASS | Unprivileged invocation exits with a clear sudo requirement |
| Official Nexus version/checksum | VERIFIED upstream metadata | 3.98.1-01 and official SHA-256 fetched from Sonatype; full Nexus archive/runtime not installed |
| Nexus service availability | NOT VERIFIED; availability probe failed | No listener at 127.0.0.1:8081; curl exit 7/HTTP 000 |
| Native installation/non-root process | NOT VERIFIED | Host systemd runs, but `sudo -n true` reports that a password is required |
| Live Maven repository configuration | NOT VERIFIED | No Nexus endpoint or administrator credentials supplied |
| Artifact upload/download | NOT VERIFIED | No live Nexus; nothing was reported published |
| Maven resolution through Nexus | NOT VERIFIED | Mirror/settings validated statically; no live Nexus to use |
| Proxy storage/cache behavior | NOT VERIFIED | Requires live proxy requests and server asset evidence |
| Multiple versions retrieved from Nexus | NOT VERIFIED | Requires publishing actual versions first |
| Live RBAC and anonymous restrictions | NOT VERIFIED | Roles/probes implemented and unit-tested; not applied to a real server |

**Total: 446 application tests passed, with 0 failures, 0 errors and 0 skips.**
All six original service builds finished with `BUILD SUCCESS`. The 29 offline
tooling tests also passed. These counts do not include a separate temporary-copy
experiment described below.

The initial restricted Docker probe was denied. The authorized elevated Maven
build could access Docker server 29.7.1. Order-service initially waited for the
real `mongo:7` image download, then completed the entire unchanged suite and
packaging successfully in 10 minutes 52 seconds. No integration tests were skipped.
While that download was pending, a temporary order-service copy used the already
cached `mongo:7.0` fixture image; all 231 tests and packaging also passed there.
Only those three temporary test fixture image strings were changed for that
experiment. Original repository tests and Docker image tags were not changed;
the result reported in the main table is the original `mongo:7` build.

## Java 11: real compatibility failures

The machine initially had Java 17/21 only. An official Eclipse Temurin
**11.0.33+10** JDK was downloaded under `/tmp`, and its SHA-256 was verified
against Adoptium release metadata. System Java was not changed. The first download
timed out; it was resumed and verified before use.

A temporary copy of discovery's POM and sources was used, preserving the service's
actual build outputs and working files. Commands:

```bash
export JAVA_HOME=/tmp/buy02-nexus-verification/java11/jdk-11.0.33+10
export PATH="$JAVA_HOME/bin:$PATH"
mvn -B -o -Dmaven.repo.local=/tmp/buy02-nexus-verification/repository \
  -f /tmp/buy02-nexus-verification/java11-discovery/pom.xml clean verify

# Diagnostic only: changing the compiler property still cannot use the frameworks.
mvn -B -o -Dmaven.repo.local=/tmp/buy02-nexus-verification/repository \
  -Djava.version=11 \
  -f /tmp/buy02-nexus-verification/java11-discovery/pom.xml clean verify
```

Both commands exited **1**. The first failed with
`release version 17 not supported`. The diagnostic override failed because
Spring Boot and Spring Cloud classes have class version **61.0**, while Java 11
expects **55.0**. Other services additionally contain records, switch expressions
and newer library APIs. This confirms an application baseline conflict, not a
Nexus configuration issue. No application Java 11 compatibility is claimed.

Application classes in all six completed executable JARs were also inspected:
they are Java 17 bytecode (major 61), consistent with the preserved POM settings.

## Configuration and tooling commands actually run

```bash
python3 scripts/nexus/manage.py audit
python3 scripts/nexus/manage.py audit --java11 # exit 1: reports all six incompatibilities
python3 -m unittest discover -s scripts/nexus -p 'test_*.py' -v
bash -n nexus/install.sh nexus/healthcheck.sh

NEXUS_URL=http://127.0.0.1:8081 mvn -B -ntp \
  -Dmaven.repo.local=/tmp/buy02-nexus-verification/repository \
  -f SERVICE/pom.xml \
  org.apache.maven.plugins:maven-help-plugin:3.4.0:effective-pom \
  -Doutput=/tmp/buy02-nexus-verification/SERVICE-effective-pom.xml
```

All six effective POMs contained these resolved URLs:

```text
http://127.0.0.1:8081/repository/maven-releases/
http://127.0.0.1:8081/repository/maven-snapshots/
```

The first offline discovery attempt and first offline help-plugin attempt failed
because dependencies were absent from the local cache. Both were rerun online
with the isolated cache and passed. Those early failures were not suppressed.

Maven's actual settings parser was exercised with `-s nexus/maven/settings.xml`
and a temporary parent-free, dependency-free POM using `validate` offline. That
passed without needing a Nexus connection; it does not prove mirror connectivity.

`systemd-analyze verify` against the real units initially reported missing
`/opt/nexus/bin/nexus` and `/usr/local/libexec/nexus-healthcheck`, as expected for
an uninstalled service. Temporary copies with `/usr/bin/true` substituted for
executables passed static unit validation. Windows-mounted source files expose
permissive mode bits; installation uses explicit 0644/0640/0750 modes on Linux.

The version workflow was executed on
`/tmp/buy02-nexus-verification/version-workflow/pom.xml`, copied from gateway:

```bash
mvn -B -ntp -Dmaven.repo.local=/tmp/buy02-nexus-verification/repository \
  -f /tmp/buy02-nexus-verification/version-workflow/pom.xml \
  org.codehaus.mojo:versions-maven-plugin:2.19.1:set \
  -DnewVersion=1.0.0 -DgenerateBackupPoms=false -DprocessAllModules=false
```

The same command with `1.0.1` and `1.0.0-SNAPSHOT` subsequently passed offline.
An XML comparison confirmed the original parent, dependencies, plugins and
deployment settings stayed unchanged. No working-tree application version was
changed and no versions were published to Nexus.

## Required live checks and exact remaining actions

An operator needs to run the installer on the selected systemd host and complete
the first-login wizard. Use the private environment setup in
[NEXUS_MAVEN_RUNBOOK.md](NEXUS_MAVEN_RUNBOOK.md); no real credentials were supplied
or written into the repository.

| Remaining check | Exact command/action |
| --- | --- |
| Install/start Nexus | `sudo bash nexus/install.sh`, then `bash nexus/healthcheck.sh` |
| Verify non-root execution | `ps -eo user,pid,comm` and `sudo systemctl status nexus`; Nexus JVM must belong to nexus |
| Verify data permissions | `sudo stat -c '%U:%G %a %n' /var/lib/nexus /var/lib/nexus/etc/nexus.properties` |
| Verify localhost binding | `sudo ss -ltnp 'sport = :8081'` |
| Create/reconcile repositories and accounts | Set private variables; `python3 scripts/nexus/manage.py provision --apply` |
| Verify configuration and least privilege roles | `python3 scripts/nexus/manage.py verify-config` |
| Verify authenticated resolution | `python3 scripts/nexus/manage.py build gateway` using a fresh NEXUS_MAVEN_CACHE |
| Verify complete project build | `python3 scripts/nexus/manage.py build all` with Docker available |
| Verify proxy caching | `python3 scripts/nexus/manage.py cache`; inspect `/var/lib/nexus/log/request.log` |
| Verify access denials | `python3 scripts/nexus/manage.py verify-access` |
| Verify snapshot upload/download | `python3 scripts/nexus/manage.py publish gateway` at the current snapshot version |
| Verify stable upload/download | `set-version gateway 1.0.0`, then `publish gateway` using the manage.py command prefix |
| Verify second stable version | `set-version gateway 1.0.1`, then `publish gateway` |
| Verify previous retrieval | `python3 scripts/nexus/manage.py resolve gateway --version 1.0.0` |
| Verify server bytes against build | `python3 scripts/nexus/manage.py verify-artifact gateway --local` |
| Verify immutable releases | Repeat a stable publication; helper must refuse and Nexus policy must remain ALLOW_ONCE |
| Capture screenshots | Follow the runbook checklist only after real server execution |

The remaining Java 11 requirement needs a coordinated application/framework
migration or an agreed correction to the project's required baseline. It cannot
be completed through Nexus settings while preserving this application's current
Spring Boot 4.1 dependencies and Java features.

## Files delivered

Modified shared files: `README.md` and `discovery/pom.xml`, `gateway/pom.xml`,
`user-service/pom.xml`, `product-service/pom.xml`, `media-service/pom.xml`,
`order-service/pom.xml` (deployment destinations only).

New files:

- `nexus/.gitignore`
- `nexus/env.example`
- `nexus/install.sh`
- `nexus/healthcheck.sh`
- `nexus/nexus.properties`
- `nexus/repositories.json`
- `nexus/maven/settings.xml`
- `nexus/systemd/nexus.service`
- `nexus/systemd/nexus-healthcheck.service`
- `nexus/systemd/nexus-healthcheck.timer`
- `scripts/nexus/nexus_api.py`
- `scripts/nexus/manage.py`
- `scripts/nexus/test_nexus.py`
- `docs/NEXUS_MAVEN_RUNBOOK.md`
- `docs/NEXUS_VERIFICATION.md`
- `docs/MY_NEXUS_PART_EXPLAINED.md`

CI/Docker integration commands, endpoint tables, required environment variables
and screenshot instructions are in the runbook. Application Dockerfiles,
Docker/CI configuration and unrelated application code were not changed.

## Follow-up verification

All six `clean verify` builds were repeated successfully using the existing
Java installation and compiler settings: **446 tests, zero failures/errors/skips**.
The unchanged **29 Nexus tooling tests** also passed again. Detailed current
PASS/FAIL/BLOCKED status and remaining private execution commands are in
[NEXUS_COMPLETION_REPORT.md](NEXUS_COMPLETION_REPORT.md).

This follow-up adds only documentation, including
[NEXUS_SCRIPTS_EXPLAINED.md](NEXUS_SCRIPTS_EXPLAINED.md) in Moroccan Darija and
[JAVA11_COMPATIBILITY.md](JAVA11_COMPATIBILITY.md). No Java/Spring Boot migration,
POM compatibility change, application rewrite, privileged Nexus installation,
commit, push or merge was performed. Live Nexus checks remain blocked by the
absent server, explicit installation approval and credentials.
