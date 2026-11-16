# My Nexus part, explained simply

My part gives our existing buy-02 Java services a place to store finished Maven
builds and a shared place to download dependencies. The application itself stays
the same. My teammate still owns Docker image publishing and the CI pipeline.

## What the three tools do

**buy-02** is our application. It has six independent Java services: discovery,
gateway, user-service, product-service, media-service and order-service. There is
also an Angular frontend. The frontend is not a Maven project.

**Maven** reads a service's `pom.xml`. It downloads libraries, compiles Java, runs
tests and packages an executable JAR. For example, gateway currently produces
`gateway/target/gateway-0.0.1-SNAPSHOT.jar`.

**Nexus** is a server that stores files used by builds. It stores our published
JARs and POMs and can keep copies of public libraries. It is not the application
server, and it does not replace Maven.

The usual dependency path is:

```text
Maven -> Nexus maven-public -> our hosted repositories or maven-central proxy
                                                    -> Maven Central if needed
```

For publishing, Maven sends our finished JAR and POM directly to a hosted
repository. We do not upload our application to the proxy or the group.

## An important Java requirement conflict

The requested Java 11 requirement does not match the repository we received.
Every service already declares Java 17. It uses Spring Boot 4.1, which needs at
least Java 17, and application code uses features such as Java records. Existing
CI uses Java 21 while Maven compiles for Java 17.

Changing the number in the POM to 11 would not make this application work on Java
11. A real migration would change application code and several frameworks. I
preserved those existing dependencies and functionality and recorded the conflict.
This requirement is still unresolved; my documentation does not pretend Java 11
compatibility was achieved. Nexus uses its own bundled Java 21 independently.

## What each file does

| File | Simple explanation |
| --- | --- |
| nexus/install.sh | Installs the pinned Nexus release on a fresh Linux systemd host, checks the download checksum, creates the nexus user, creates persistent storage and starts the service |
| nexus/nexus.properties | Makes Nexus listen only on 127.0.0.1:8081 and keeps server-side script creation disabled |
| nexus/systemd/nexus.service | Tells Linux to run Nexus as nexus, start it after reboot, wait for readiness and restart it after a crash |
| nexus/systemd/nexus-healthcheck.service | Runs the small healthcheck under the nexus account |
| nexus/systemd/nexus-healthcheck.timer | Runs that check every minute after startup |
| nexus/healthcheck.sh | Checks whether Nexus can handle reads and writes; returns failure when either check fails |
| nexus/repositories.json | Describes the four Maven repositories and their rules |
| nexus/maven/settings.xml | Sends dependency/plugin downloads to Nexus and reads credentials from environment variables |
| nexus/env.example | Lists the environment variables to supply privately; it contains no real passwords |
| nexus/.gitignore | Helps keep private settings, passwords, downloads and Nexus data out of Git |
| Each service's pom.xml | Keeps the original application build and adds release/snapshot upload destinations |
| scripts/nexus/nexus_api.py | Handles authenticated Nexus requests, safe configuration comparisons and artifact paths |
| scripts/nexus/manage.py | Provides commands to provision repositories/roles, build, publish, retrieve and verify artifacts |
| scripts/nexus/test_nexus.py | Tests the tooling offline, including secret handling, permissions, repository collisions and snapshot paths |
| docs/NEXUS_MAVEN_RUNBOOK.md | Contains the complete setup, commands, security details and troubleshooting |
| docs/NEXUS_VERIFICATION.md | Records the checks actually run, their real results and remaining checks |

The existing coordinates are preserved. Gateway is
`com.buy01:gateway:0.0.1-SNAPSHOT`. Media is
`com.buy-01:media:0.0.1-SNAPSHOT`; the different media group/artifact names were
already in its POM. Renaming them would create different artifact coordinates.
JAR packaging is preserved because these services are executable Spring Boot
applications. They do not need to become WAR projects for Nexus.

## How Nexus starts and keeps files

On the intended Linux host, run `sudo bash nexus/install.sh` from the repository
root. The script uses the official Nexus Community Edition 3.98.1-01 archive,
the current free successor to the older OSS binary distribution. It does not
change the Java version used to build buy-02.

Nexus runs as a dedicated account named `nexus`, not root. Its application is
under `/opt/nexus`; its database, artifact files, logs and configuration are under
`/var/lib/nexus`. Stopping or restarting the service does not delete these files.
The installer refuses to overwrite an existing unmanaged installation.

The web address is `http://127.0.0.1:8081/` on that host. For the first login,
the administrator reads `/var/lib/nexus/admin.password` privately, signs in as
`admin`, changes the password and finishes the setup wizard. That password never
belongs in the repository.

The localhost setting means remote visitors cannot connect directly. For a lab,
use an SSH tunnel. Shared remote builders need a private HTTPS endpoint with
trusted certificates and access restrictions. The runbook explains both cases.

The restricted development shell cannot control systemd. A check outside it
confirmed that the host has systemd, but administrator access requires a sudo
password. The installer and configuration are prepared; actual installation and
live server verification remain actions to perform on the designated host.

## What the four repositories mean

| Name | What it does | Concrete example |
| --- | --- | --- |
| maven-releases | Stores stable versions and refuses overwriting an existing release asset | gateway 1.0.0 |
| maven-snapshots | Stores development builds, including repeated snapshots | gateway 1.0.0-SNAPSHOT |
| maven-central | Fetches public libraries from Maven Central and keeps them in Nexus | commons-lang3 3.17.0 |
| maven-public | Gives Maven one download address for all three repositories | resolve our gateway JAR or a public dependency |

A **hosted** repository holds things we upload. A **proxy** fetches things from
another server. A **group** combines several repositories behind one address.
The provisioning command checks existing repositories so rerunning it does not
create duplicate repositories or delete existing artifacts.

## Why Maven settings and the POM both changed

The POM describes the project and upload destinations. Its
`distributionManagement` section says where Maven should publish stable releases
and development snapshots.

The settings file describes how this particular Maven invocation connects.
Its mirror sends dependency and plugin resolution through `maven-public`. Its
server entries supply the credentials for that mirror and the two upload
destinations. The IDs must match:

```text
nexus-public    -> reader credentials for downloading through the group
nexus-releases  -> publisher credentials for stable uploads
nexus-snapshots -> publisher credentials for snapshot uploads
```

The repository name `maven-releases` and the credential ID `nexus-releases` do
different jobs. The first is part of the server URL; the second selects a
credential entry in Maven settings.

Passwords use placeholders such as `${env.NEXUS_PUBLISH_PASSWORD}`. The shell
or secret manager supplies their real values. We pass the settings with `-s`, so
other projects' global Maven settings are preserved.

## How artifact publishing works

After installation, account/repository provisioning and private environment setup:

```bash
python3 scripts/nexus/manage.py build gateway
python3 scripts/nexus/manage.py publish gateway
```

`build` runs `clean verify`. `publish` runs `clean deploy`, which also includes
tests and verification before the upload phase. If tests fail, the helper stops.
It does not bypass tests to get an upload to succeed.

Maven uploads the JAR, its POM, checksums and repository metadata. A snapshot
upload goes to maven-snapshots; a stable version goes to maven-releases.

After deployment, the helper downloads the JAR and POM again from Nexus and
compares their SHA-256 checksums with the local files. It also checks the group
download. A checksum is a fingerprint of a file. Matching fingerprints show that
we retrieved the same bytes we built.

Only then does it print `CONFIRMED available`. A successful Maven command by
itself is not reported as a verified publication. No real publication is claimed
while the server and credentials are unavailable.

## How the proxy and cache work

Suppose Maven needs `org.apache.commons:commons-lang3:3.17.0`. It asks the group.
The group can ask maven-central, which fetches the library from Maven Central
when needed and stores it on Nexus's persistent disk. Later builds can reuse
that stored copy.

There are two different caches: Maven's local cache on the developer machine and
Nexus's server cache. A repeated build can succeed from Maven's cache without
contacting Nexus. That is why the runbook uses two fresh Maven cache directories
when demonstrating the proxy.

The command below also downloads a public dependency twice without using a
Maven local cache and checks the stored proxy asset through the server API:

```bash
python3 scripts/nexus/manage.py cache
```

Incoming request logs show that requests reached Nexus. The stored proxy asset
and matching hashes provide additional cache evidence. For stronger offline
evidence, the runbook describes a temporary outbound-block test after fetching
the artifact; it must be coordinated because the setting affects other builds.

## How version numbers work

`1.0.0-SNAPSHOT` means a development version that may be published several times.
Nexus stores timestamped snapshot files and metadata telling Maven which build
is the latest. `1.0.0` and `1.0.1` are two different stable versions.

Use the provided helper to change only the service's version:

```bash
python3 scripts/nexus/manage.py set-version gateway 1.0.0
git diff -- gateway/pom.xml
python3 scripts/nexus/manage.py publish gateway
python3 scripts/nexus/manage.py set-version gateway 1.0.1
python3 scripts/nexus/manage.py publish gateway
python3 scripts/nexus/manage.py resolve gateway --version 1.0.0
```

The last command retrieves the previous stable version. Nexus does not replace
1.0.0 when 1.0.1 is published. Release overwrite protection also stops someone
from silently replacing 1.0.0 with different bytes. If a release upload was
partial, choose a new version instead of weakening that protection.

These demonstration commands are to run against the real configured instance.
They were not already published in this development environment.

## Authentication and RBAC

**Authentication** answers “Who are you?” using a username and password.
**RBAC** means role-based access control: a user's role decides what they may do.

- The administrator configures Nexus and users.
- The reader downloads from maven-public.
- The publisher also uploads to the two hosted Maven repositories.
- The publisher cannot administer users or delete artifacts.
- Anonymous visitors cannot download project artifacts.

The publisher needs repository add/edit permissions because Maven uses uploads
and updates metadata. The server's release policy still protects existing stable
artifact files. Service accounts never receive the administrator role.

Provisioning creates the two roles and missing accounts using Nexus's REST API.
It refuses unexpected existing account roles and does not reset existing
passwords. The `verify-access` command checks allowed reads and rejected actions;
real release/snapshot publishing verifies the positive upload path.

## How I can demonstrate my part during evaluation

1. Explain the Java baseline conflict honestly, then show the exact verification
   report. Do not describe unexecuted checks as successful.
2. On the configured host, show the Nexus service running under the nexus user,
   its persistent storage and localhost listener.
3. Show the four repositories in the web interface, Central's remote URL and the
   group's three members. Show release overwrite protection.
4. Show the settings placeholders and POM deployment URLs without revealing
   secret values. Explain the reader and publisher roles.
5. Run a real service build and show the tests. For order-service, provide Docker
   for its existing MongoDB integration tests.
6. Publish a snapshot and a stable version, show the actual Nexus assets and the
   helper's downloaded checksum verification.
7. Publish another stable version and retrieve the older exact version.
8. Demonstrate a public dependency fetch with fresh Maven caches, inspect the
   stored proxy asset and request logs, and explain the two different caches.
9. Run `verify-access` and show that anonymous reads and unauthorized writes are
   rejected. Capture screenshots only from these real results.
10. Give the teammate the Maven URLs, settings path, four reader/publisher secret
    names and publishing commands. Their CI job must not receive admin credentials.

Follow [the full runbook](NEXUS_MAVEN_RUNBOOK.md) for exact installation, private
environment setup, publishing commands, troubleshooting and the screenshot list.
