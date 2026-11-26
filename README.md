# Buy02

Buy02 is a Spring Boot microservices and Angular marketplace: products/images,
search and price sliders, shopping cart, Pay on Delivery, orders and customer/seller
analytics.

**On a new PC, follow steps 1–7 below in order.** Commands use **Bash on Linux**
from the repository root. They configure the existing host-Docker Jenkins setup;
you do not need Docker-in-Docker. Windows/macOS host setup is not covered here.

| What you want | URL after startup |
| --- | --- |
| Staging app built by Jenkins | **https://localhost:4300** |
| Jenkins | **http://localhost:8085** |
| SonarQube | **http://localhost:9000** |
| Optional local development app | https://localhost:4200 |

Port 4300 is used for staging; the optional development app uses 4200.
A fresh PC starts with empty application databases;
create your seller/client accounts through the website. Secrets and existing
application data are not included in a Git clone.

## 1. Install prerequisites and clone

For the Jenkins/staging path install:

- Git, Docker Engine with Docker Compose v2, Python 3, OpenSSL, curl and `iproute2`.
- A browser and a Cloudinary account with working image-upload credentials.
- Internet access for Docker images, Jenkins plugins, Maven/npm dependencies and
  Cloudinary. Allow sufficient free RAM and disk for the builds and SonarQube.

Use the [Docker Engine installation instructions](https://docs.docker.com/engine/install/)
for your Linux distribution. Your normal user must be able to run Docker commands
without `sudo`, using either rootless Docker or your configured Docker permissions.
Jenkins contains Java 21, Node.js 24.20.0 and the build tools; host Java/npm are only
needed for the optional development/testing commands later in this README.

```bash
git --version
docker info
docker compose version
python3 --version
openssl version
curl --version
ip -4 route

git clone https://github.com/AyyoubMh48/buy-02.git
cd buy-02
```

Prepare the Linux host for SonarQube's embedded Elasticsearch:

```bash
sysctl vm.max_map_count
sysctl fs.file-max
ulimit -n
ulimit -u
```

The documented requirements are at least 524288 memory-map areas, 131072 file
descriptors and 8192 threads. If your values are lower, have the host administrator
apply the [SonarQube Linux prerequisites](https://docs.sonarsource.com/sonarqube-community-build/server-installation/pre-installation/linux).
For example, a lower memory-map limit can be raised with:

```bash
sudo sysctl -w vm.max_map_count=524288
```

That command lasts until reboot; the linked instructions explain persistent
settings and service limits. These are host prerequisites, not application settings.

## 2. Create private configuration — fresh PC only

This block generates new JWT, database, TLS-keystore and Sonar database passwords.
It stops if either configuration already exists, so it does not overwrite an
existing installation. Run it only for the first setup on a new PC.

```bash
umask 077
python3 - <<'PY'
from pathlib import Path
import secrets

folder = Path('jenkins-lab/jenkins-secrets')
app = folder / 'buy01-env'
sonar = Path('jenkins-lab/.env')
if app.exists() or sonar.exists():
    raise SystemExit('Configuration already exists. Keep it and continue with the next step.')
folder.mkdir(parents=True, exist_ok=True)
folder.chmod(0o700)
values = {'JWT_SECRET': secrets.token_hex(32), 'MONGO_ROOT_USERNAME': 'buy02_admin'}
for name in ('SERVER_SSL_KEY_STORE_PASSWORD', 'MONGO_ROOT_PASSWORD',
             'PRODUCT_MONGO_PASSWORD', 'MEDIA_MONGO_PASSWORD',
             'USER_MONGO_PASSWORD', 'ORDER_MONGO_PASSWORD'):
    values[name] = secrets.token_hex(24)
lines = []
for line in Path('.env.example').read_text().splitlines():
    key = line.split('=', 1)[0]
    lines.append(f'{key}={values[key]}' if key in values else line)
app.write_text('\n'.join(lines) + '\n')
sonar.write_text('SONAR_DB_PASSWORD=' + secrets.token_hex(24) + '\n')
app.chmod(0o600)
sonar.chmod(0o600)
print('Created private configuration. Set the three Cloudinary values next.')
PY
```

Open **`jenkins-lab/jenkins-secrets/buy01-env`** in your editor and replace only
these three example values with your Cloudinary account values:

| Variable | Where its value comes from |
| --- | --- |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary dashboard's **Cloud name**, not the key's display name |
| `CLOUDINARY_API_KEY` | The active API key |
| `CLOUDINARY_API_SECRET` | The matching API secret |

Use valid `KEY=value` lines; quote values containing shell-special characters.
Keep the generated JWT/database/keystore values. Staging rejects unchanged example
Cloudinary values; image upload cannot work without real provider credentials.
Use current private credentials, not values copied from old source history.

Create the Jenkins administrator password using a hidden prompt:

```bash
read -rsp 'Choose a Jenkins admin password: ' buy02_admin_password; echo
printf '%s\n' "$buy02_admin_password" > jenkins-lab/jenkins-secrets/jenkins-admin-password
unset buy02_admin_password
chmod 600 jenkins-lab/jenkins-secrets/jenkins-admin-password
```

This public repository needs no GitHub PAT. Leave `github-username` and `github-pat`
absent. They are optional for a private repository. Keep all secret files out of Git
and chat. Legacy internal names such as `buy01-env`, Java packages, browser storage
keys, Sonar project keys and volume names remain for compatibility; the website
brand is BUY02.

## 3. Generate matching HTTPS certificates

Run once for this fresh installation. The PKCS12 password is read from the
configuration generated above, so the gateway and keystore use the same password.

```bash
openssl req -x509 -newkey rsa:2048 -sha256 -nodes -days 365 \
  -keyout jenkins-lab/jenkins-secrets/gateway-keystore.key \
  -out jenkins-lab/jenkins-secrets/gateway-keystore.crt \
  -subj '/CN=localhost' \
  -addext 'subjectAltName=DNS:localhost,DNS:gateway,IP:127.0.0.1'

buy02_keystore_password=$(sed -n 's/^SERVER_SSL_KEY_STORE_PASSWORD=//p' jenkins-lab/jenkins-secrets/buy01-env)
export buy02_keystore_password
openssl pkcs12 -export -name gateway \
  -inkey jenkins-lab/jenkins-secrets/gateway-keystore.key \
  -in jenkins-lab/jenkins-secrets/gateway-keystore.crt \
  -out jenkins-lab/jenkins-secrets/gateway-keystore.p12 \
  -passout env:buy02_keystore_password
unset buy02_keystore_password
chmod 600 jenkins-lab/jenkins-secrets/*
```

These are self-signed local certificates. Accept/trust the localhost certificate
in your browser. On an existing installation, keep its certificates and
matching password rather than rerunning fresh-install steps.

## 4. Start SonarQube and create its token

```bash
docker compose --env-file jenkins-lab/.env -p jenkins-lab -f jenkins-lab/compose.yml config --quiet
docker compose --env-file jenkins-lab/.env -p jenkins-lab -f jenkins-lab/compose.yml \
  up -d --wait --wait-timeout 900 sonar-db sonarqube
```

Open **http://localhost:9000**. On a fresh instance sign in with `admin` / `admin`,
change the password, then open **My Account → Security → Generate Tokens**.
Generate an administrator **User Token** (not a Project Analysis Token).

Save it using the hidden prompt:

```bash
read -rsp 'SonarQube administrator User Token: ' buy02_sonar_token; echo
printf '%s\n' "$buy02_sonar_token" > jenkins-lab/jenkins-secrets/sonar-bootstrap-token
unset buy02_sonar_token
chmod 600 jenkins-lab/jenkins-secrets/sonar-bootstrap-token
```

Provision the seven projects, analysis tokens, exact project keys and internal
Jenkins quality-gate webhook:

```bash
docker compose --env-file jenkins-lab/.env -p jenkins-lab -f jenkins-lab/compose.yml \
  --profile bootstrap run --rm --no-deps sonar-init
```

Expected final message: **`Provisioning complete; recreate Jenkins to load secret files`**.
The bootstrap preserves existing valid projects/tokens on rerun; do not manually
create seven tokens or delete SonarQube volumes. Its project keys are
`buy01-product-service`, `buy01-user-service`, `buy01-media-service`,
`buy01-order-service`, `buy01-gateway`, `buy01-discovery`, `buy01-frontend`.

## 5. Start Jenkins and verify its configuration

```bash
bash scripts/run-jenkins-host.sh
```

The launcher creates/reuses the Jenkins home and network, detects your Unix Docker
socket and host IPv4 address, and starts Jenkins without privileged DinD. Its
private host settings are saved in `.local/jenkins-host.env`. This Linux setup uses
one local Docker daemon; run trusted team builds only. If automatic address
selection is wrong, rerun with `JENKINS_TEST_HOST=<reachable-host-ip>`.

Open **http://localhost:8085**, username **`admin`**, with the password from step 2.
Check that these jobs exist:

| Job | Purpose |
| --- | --- |
| `first-pipeline` | Test/scan/build remote main and deploy staging |
| `pull-request-checks` | Build/test a selected team PR before merging; no deployment stage |

Verify the actual loaded Sonar credentials and permissions:

```bash
docker cp Jenkinsfile jenkins:/tmp/Buy02.Jenkinsfile
docker exec -i -e JENKINSFILE_TO_VALIDATE=/tmp/Buy02.Jenkinsfile \
  jenkins node < jenkins-lab/sonar-init/verify-jenkins.js
```

Expect **`Jenkinsfile successfully validated`**, seven **`PASS`** lines and
**`SAFE_ZONE_VERIFY_PASSED`**. JCasC configuration files alone do not establish that
Jenkins loaded the credentials. After changing secret files, wait for active builds
to finish and rerun the launcher so Jenkins reloads its startup credentials.

## 6. Build and deploy the application

Open **first-pipeline → Build Now → Console Output**. It checks out this repository's
remote **main**, not local uncommitted files or a feature branch. No extra Jenkins
credential entry is needed after the bootstrap and verification above.

The run executes backend/frontend builds and tests, coverage, all seven Sonar
analyses/gates, Docker image packaging, deployment and container health checks.
Images use the Jenkins build number. A failing test/gate prevents later deployment.
Use **Build Now** to deploy the application. Scheduled runs skip deployment.

When it finishes, check **Deploy** and **Post-Deployment Health Check** are both
**SUCCESS**, then open **https://localhost:4300**. The first visit may require
accepting the local certificate. Confirm catalog requests actually work; container
health alone does not verify API access.

Register a **Merchant** account to add products with images, or a **Client** account
to browse and place Pay on Delivery orders. Use the profile page to update account
details and view analytics.

```bash
docker ps --filter name=buy02-staging
curl -kfsS https://localhost:4300/api/products/search
```

The app uses separate `buy02-staging-*` containers and database volumes. Its gateway
is loopback 8445, Kafka loopback 19092 and MongoDB loopback 37017/37019/37020/37021.
The frontend proxies `/api/**` to the gateway; services communicate through Eureka
and Kafka. Certificates and Mongo initialization scripts are copied into dedicated
named volumes so paths inside Jenkins are not mistaken for host filesystem paths.

## 7. Stop, restart and update

Stop or resume the already deployed app without changing its images or data:

```bash
docker ps -aq --filter label=com.docker.compose.project=buy02-staging | xargs -r docker stop
docker ps -aq --filter label=com.docker.compose.project=buy02-staging | xargs -r docker start
```

Starting containers may take time for Eureka registration and gateway routes to
recover. Check health and the real catalog again. To deploy a reviewed code update:

1. Merge its PR with green required checks and teammate approval.
2. `git pull --ff-only` on main in the host checkout to update mounted Jenkins config.
3. After active builds finish, rerun `bash scripts/run-jenkins-host.sh` if configuration
   or secrets changed, then **first-pipeline → Build Now**.

Keep secret files and Docker volumes between restarts. Changing a password in an
environment file does not change the user already initialized in Mongo/PostgreSQL.
Do not use volume deletion or `docker compose down -v` as ordinary restart commands.

## Development workflow and code quality

For a new team PR, open **pull-request-checks → Build with Parameters**, enter its
GitHub number as `PR_NUMBER`, and run it. Include that build link in the PR manually.
The controller-owned validator accepts same-repository PRs into main from trusted
team members, pins the exact head and merges current main for the build/tests.
Fork/untrusted author builds are rejected by this Docker lab. GitHub Actions
additionally runs unit, integration and browser E2E tests, builds, and isolated
whole-code Sonar scans. Main requires one approval, an up-to-date branch and green
**Tests and SonarQube gates** from GitHub Actions. Current configuration is recorded
in [.ci/main-ruleset.json](.ci/main-ruleset.json).

Jenkins retains main analysis history in the local SonarQube server. GitHub Actions
creates a disposable SonarQube server per run, so PR scans do not overwrite main.
Inspect its summary and `quality-<run>-<attempt>` artifact for results, coverage and
failure screenshots. The gate enforces at least 80% coverage, zero bugs/vulnerabilities/
code smells, zero new issues, limited new duplication and reviewed security hotspots.
Frontend additionally enforces 80% in statements, branches, functions and lines.

SonarQube improvements:

| Feedback | Improvement |
| --- | --- |
| `java:S1612` in order tests | Replaced a trivial lambda with `StatusChange::status` |
| `java:S2143` in analytics | Used `java.time`/UTC Instant date boundaries instead of legacy Date |
| `Web:S6821` on an Angular input named role | Renamed that input to `audience` |
| `Web:S6845` on non-interactive containers | Removed inappropriate tabindex attributes |
| `java:S1192` repeated Mongo expressions | Introduced shared operator/field constants |
| `java:S8924` Mockito test imports | Used the required static-import style without weakening assertions |

## Optional local development and automated tests

To build outside Jenkins, also install **Java 21 and Node.js 24.20.0/npm** on the
host. Maven wrappers download Maven; you do not need a separate Maven install.

```bash
java -version
node --version
npm --version
bash scripts/run-local.sh
```

This builds a separate local stack at **https://localhost:4200**. Its generated
configuration/certificates live under `.local/`. Set the three CLOUDINARY_* values
in `.local/app.env` and rerun the script for local uploads. This is a different
configuration and database from staging. The script generates secrets only if its
file is absent. This path supports development and the automated local E2E fixtures.

Backend unit/integration tests (Docker must be running for disposable MongoDB):

```bash
for service in product-service user-service media-service order-service gateway discovery; do
  (cd "$service" && bash ./mvnw -B clean verify) || exit 1
done
```

Frontend coverage, build and browser suite:

```bash
cd frontend
npm ci
npm run test:coverage
npm run build
npx puppeteer browsers install chrome
export PUPPETEER_EXECUTABLE_PATH="$(node --input-type=module -e 'import puppeteer from "puppeteer"; console.log(await puppeteer.executablePath())')"
cd ..
bash scripts/run-local.sh --skip-build
(cd frontend && npm run test:e2e)
```

The browser suite is fixed to the isolated **buy02-local** stack on 4200 and refuses
fixture writes to other Compose projects. Its eight scenarios cover search/sliders,
checkout, mixed sellers, cancellation, analytics/mobile dates, archive, API errors
and profile picker/save persistence. It creates random accounts/product fixtures
and removes its own records; product fixtures bypass Cloudinary. For real image
uploads, configure Cloudinary and use the seller product form. Failures save screenshots under ignored
`frontend/e2e/artifacts/`. CI sets `E2E_NO_SANDBOX=1` for its disposable runner;
use that option locally only if Chrome's sandbox cannot run in your environment.

Configuration/helper checks:

```bash
python3 -m unittest discover -s jenkins-lab/sonar-init -p 'test_*.py'
python3 -m unittest discover -s .ci -p 'test_*.py'
bash -n scripts/run-local.sh scripts/run-jenkins-host.sh jenkins-lab/docker-entrypoint.sh
```

## API and security reference

Browser requests use `/api` through Nginx and the gateway. Public catalog reads need
no login; protected requests use the JWT from login. Mutations also require the
CSRF cookie and `X-XSRF-TOKEN` obtained from `GET /api/csrf`; Angular handles both.
The gateway strips caller-supplied X-User-* headers and forwards verified identity.
Backend services enforce roles and ownership; only the gateway is the public API.
Authentication endpoints are necessarily available before login.

| Endpoint group | Main operations |
| --- | --- |
| `/api/auth/register`, `/api/auth/login` | Account creation/login |
| `/api/me` | GET/PUT own profile; seller avatar uses owned media |
| `/api/products/search` | GET keywords/category/minPrice/maxPrice/inStock/sort/page/size |
| `/api/products` | Seller create/edit/delete; own-product checks |
| `/api/media/images` | Seller image upload, maximum 2 MB; owned deletion |
| `/api/cart` | Client read/clear; `/items` add and `/items/{id}` update/remove |
| `/api/cart/review`, `/api/cart/checkout` | Review and confirm with delivery address and Idempotency-Key |
| `/api/orders/my`, `/api/orders/seller` | Paginated role-scoped lists with status/from/to/q filters |
| `/api/orders/{id}` | Owned details; `/cancel`, `/reorder`, `/status`, `/archive` actions |
| `/api/orders/analytics/me`, `/api/orders/analytics/seller` | Date-filtered customer/seller reports |

Finished-order removal is a personal archive, preserving snapshots and analytics.
Reorder adds available products to the cart for review; it does not silently place
a new order. Only delivered seller lines count in analytics. Date ranges include
both placement-day endpoints in UTC; seller reports never include another seller's
items. A mixed order stays In progress until its parts finish. All delivered becomes
Delivered; all cancelled becomes Cancelled; a terminal mixture becomes Completed.

Application errors follow `{ "code": "VALIDATION_FAILED", "message": "Invalid input data", "details": { "field": "Reason" } }`.
`details` is an object, including `{}` when no field detail applies. Typical statuses
are 400 validation, 401 authentication, 403 permissions/CSRF, 404 missing resource,
409 conflict, 502 provider failure and 503 unavailable dependency. Unexpected 500s
hide implementation details. Error responses exclude credentials, rejected secrets
and stack traces. Angular renders field details inline and safe general messages.

## Troubleshooting

| Symptom | Check/action |
| --- | --- |
| Docker permission denied | Fix your user's daemon/socket access; rerun `docker info` |
| SonarQube exits or stays unhealthy | Host limits, free memory/disk, then `docker compose --env-file jenkins-lab/.env -p jenkins-lab -f jenkins-lab/compose.yml logs --tail=80 sonarqube sonar-db`; redact secrets before sharing |
| Missing Sonar credentials/server in Jenkins | Run bootstrap, then recreate Jenkins with the launcher and run the verifier |
| Jenkins Docker/Testcontainers cannot connect | Check `.local/jenkins-host.env`; use a reachable host IP; rerun the launcher |
| Upload fails | Configure real Cloudinary values in the correct staging/local file, reload Jenkins secrets and redeploy for staging |
| Gateway fails to read PKCS12 | Keystore password must match SERVER_SSL_KEY_STORE_PASSWORD; preserve or regenerate a matching pair |
| App health green but API temporarily fails | Allow Eureka/gateway registration caches to refresh; check real catalog and authenticated order requests |
| Mongo/PostgreSQL authentication fails after editing passwords | Restore initialized credentials; changing env files does not migrate existing DB users |
| UI still shows old branding or behavior | Confirm reviewed main was deployed by Jenkins, then refresh the browser |
| GitHub check queued | It has not started a runner; inspect job steps before assuming a code failure |

Legacy `jenkins-lab/compose.yml` also supports the original privileged DinD lab;
`sonar-lab/compose.yml` is a compatibility include. The primary steps above use the
host-daemon controller file explicitly. Preserve legacy named volumes when updating
an existing installation; a new PC should follow the fresh setup without importing
other people's passwords or using reset/delete-volume commands.

## Nexus setup and publishing

Run these commands from the repository root. You need Docker with Compose v2,
Python 3, OpenSSL and the JDK listed in the local development section. The six
Spring Boot services already have Maven wrappers and build executable JARs.

### 1. Start Nexus

Create local TLS certificates once, then start Nexus and its registry proxy.
Reuse the same Compose project and data volume if Nexus is already installed.

```bash
test -d .local/nexus-tls || bash scripts/nexus/create_registry_tls.sh
export NEXUS_TLS_DIR="$PWD/.local/nexus-tls"
docker compose -p nexus -f nexus/docker-compose.yml -f nexus/compose.registry.yml \
  up -d --wait --wait-timeout 900
curl -fsS http://127.0.0.1:8081/service/rest/v1/status/writable
docker compose -p nexus -f nexus/docker-compose.yml exec -T nexus id
```

Nexus should be writable and run as the non-root user with UID `200`. The
`buy02-nexus-data` volume retains repositories and artifacts between restarts.
Open [Nexus](http://127.0.0.1:8081). For a fresh instance, follow the first-login
steps, accept the license agreement and disable anonymous access.
See the [Maven runbook](docs/NEXUS_MAVEN_RUNBOOK.md#fresh-clone-onboarding-for-teammates).

### 2. Set up Maven repositories

After first login, run the credential helper once. Enter the administrator
credentials and choose separate reader and publisher credentials. If the private
file already exists, skip the helper and load the existing file.

```bash
python3 scripts/nexus/setup_credentials.py \
  --url http://127.0.0.1:8081 --file /tmp/buy02-nexus-team.env
set -a
source /tmp/buy02-nexus-team.env
set +a
python3 scripts/nexus/manage.py provision
```

Review the plan, then apply and verify it.

```bash
python3 scripts/nexus/manage.py provision --apply
python3 scripts/nexus/manage.py verify-config
```

| Repository | Use |
| --- | --- |
| `maven-releases` | Hosted release JARs |
| `maven-snapshots` | Hosted snapshot JARs |
| `maven-central` | Proxy and cache for Maven Central |
| `maven-public` | Group endpoint for dependency and plugin resolution |

### 3. Publish, retrieve and verify Maven artifacts

On eligible main builds, Jenkins publishes the existing backend JARs and
original POMs with Maven's `deploy-file` goal after the SonarQube Quality Gates.
For manual publishing, load the Buy02 application environment if needed for
tests. `manage.py publish` builds and tests the services using
`nexus/maven/settings.xml`. Use an empty local Maven cache to demonstrate
dependency downloads through `maven-public`.

```bash
export NEXUS_MAVEN_CACHE="$(mktemp -d)"
python3 scripts/nexus/manage.py publish all
python3 scripts/nexus/manage.py verify-artifact discovery --local
python3 scripts/nexus/manage.py resolve discovery --version 0.0.1-SNAPSHOT
python3 scripts/nexus/manage.py cache
unset NEXUS_MAVEN_CACHE
```

Check that the JAR and POM checksums match and the dependency is visible in
`maven-central`. To demonstrate version retrieval, use a separate test checkout
and two unused versions. For example, publish `discovery` twice with distinct
versions, then resolve both and verify that the older artifact is still available.

```bash
python3 scripts/nexus/manage.py set-version discovery 0.1.0
python3 scripts/nexus/manage.py publish discovery
python3 scripts/nexus/manage.py set-version discovery 0.1.1
python3 scripts/nexus/manage.py publish discovery
python3 scripts/nexus/manage.py resolve discovery --version 0.1.0
python3 scripts/nexus/manage.py resolve discovery --version 0.1.1
```

### 4. Publish and retrieve Docker images

Create the private Docker credential file once. Use the default usernames and
press Enter at the password prompts to generate passwords for new accounts.
Keep the Maven credentials loaded for repository provisioning.

```bash
python3 scripts/nexus/setup_docker_credentials.py
set -a
source .local/nexus-docker.env
set +a
python3 scripts/nexus/registry.py
```

Review the plan, then run `python3 scripts/nexus/registry.py --apply` followed
by `python3 scripts/nexus/registry.py --verify`. Configure certificate trust
for the Docker CLI and daemon before logging in.
See the [TLS setup](docs/NEXUS_DOCKER_CI_RUNBOOK.md#3-configure-dns-and-certificate-trust).

With the Maven JARs built and the registry CA trusted, push and pull the six
backend images. Use a new build number and manifest filename for each run.

```bash
export NEXUS_DOCKER_REGISTRY=localhost:5443
export NEXUS_CA_BUNDLE="$NEXUS_TLS_DIR/ca.crt"
python3 scripts/nexus/images.py build --source-tag local-1
release_tag=$(python3 scripts/nexus/images.py tag --build 1)
python3 scripts/nexus/images.py publish --source-tag local-1 --tag "$release_tag" \
  --manifest reports/nexus/local-1.json
python3 scripts/nexus/images.py pull --manifest reports/nexus/local-1.json
```

The manifest records the Git commit and image digests. To retrieve a previous
release, pass its saved manifest to the same `pull` command.

### 5. Verify Jenkins publishing

Configure the registry hostname, certificates and credentials in Jenkins, then
start it with the Nexus network enabled.
See the [Jenkins setup](docs/NEXUS_DOCKER_CI_RUNBOOK.md#5-connect-jenkins-and-configure-credentials).

```bash
NEXUS_CI_NETWORK=true bash scripts/run-jenkins-host.sh
```

Check that a regular push to `main` triggers Jenkins. In the build log, verify
that tests and quality gates pass before publishing. Confirm that Nexus contains
the Maven JARs and all seven Docker images, including the frontend, and that
Jenkins archives the release manifest. Check that staging becomes healthy.

### 6. View the audit evidence

The [completion report](docs/NEXUS_COMPLETION_REPORT.md#jenkins-build-12-and-rollback-build-13)
documents the successful Jenkins build #12, its seven SonarQube Quality Gates,
and the controlled build #13 that recovered release #12. The
[Maven runbook](docs/NEXUS_MAVEN_RUNBOOK.md#repository-layout-and-access)
and [Docker CI runbook](docs/NEXUS_DOCKER_CI_RUNBOOK.md#4-build-publish-and-verify-images)
show the live Nexus inventories and commands for publishing, inspecting,
and retrieving releases.
