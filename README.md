# Buy01 — Microservices E-Commerce Platform

Buy01 is a containerized e-commerce platform built with **Spring Boot microservices**, **Angular**, **MongoDB**, **Apache Kafka**, **Eureka Service Discovery**, **Spring Cloud Gateway**, and **Docker**.

The project also includes a **Jenkins CI/CD pipeline** responsible for automatically testing, packaging, and containerizing the application.

---

## Architecture

```text
                         ┌─────────────────────────┐
                         │     Angular Frontend    │
                         │       Port 4200         │
                         └────────────┬────────────┘
                                      │
                                      │ HTTPS
                                      ▼
                         ┌─────────────────────────┐
                         │       API Gateway       │
                         │   JWT / Routing / CORS  │
                         └────────────┬────────────┘
                                      │
                 ┌────────────────────┼────────────────────┐
                 │                    │                    │
                 ▼                    ▼                    ▼
        ┌────────────────┐   ┌────────────────┐   ┌────────────────┐
        │  User Service  │   │Product Service │   │ Media Service  │
        │     8081       │   │     8082       │   │     8083       │
        └───────┬────────┘   └───────┬────────┘   └───────┬────────┘
                │                    │                    │
                ▼                    ▼                    ▼
           User MongoDB        Product MongoDB       Media MongoDB

                 └────────────────────┬────────────────────┘
                                      │
                            ┌─────────▼─────────┐
                            │ Eureka Discovery │
                            │       8761       │
                            └───────────────────┘

                            ┌───────────────────┐
                            │   Apache Kafka    │
                            │       9092        │
                            └───────────────────┘
```

Each business service owns its own MongoDB database and private Docker network.

The application services also share the `buy01-network` for service discovery and inter-service communication.

---

## Services

| Service | Internal Port | Responsibility |
|---|---:|---|
| Discovery Service | `8761` | Eureka service registry |
| API Gateway | `8080` | Routing, JWT validation, CORS and user header forwarding |
| User Service | `8081` | Authentication, JWT generation and user profiles |
| Product Service | `8082` | Product CRUD, seller ownership and image associations |
| Media Service | `8083` | Image validation, upload metadata and Cloudinary integration |
| Frontend | `443` | Angular SPA served by Nginx |
| User MongoDB | `27017` | User Service database |
| Product MongoDB | `27017` | Product Service database |
| Media MongoDB | `27017` | Media Service database |
| Kafka | `9092` | Asynchronous application events |

MongoDB is exposed to the host only when needed:

```text
User MongoDB      localhost:27017
Product MongoDB   localhost:27019
Media MongoDB     localhost:27020
```

---

## Technology Stack

### Backend

- Java 17
- Spring Boot
- Spring Security
- Spring Cloud Gateway
- Netflix Eureka
- Spring Data MongoDB
- Spring Kafka
- Maven Wrapper
- Spring Boot Actuator

### Frontend

- Angular
- TypeScript
- Vitest / Angular Test Runner
- Nginx

### Infrastructure

- Docker
- Docker Compose
- MongoDB 7
- Apache Kafka
- Jenkins
- Docker-in-Docker
- Git / GitHub

### External Services

- Cloudinary

---

# Project Structure

```text
mr-jenk/
│
├── discovery/
│   ├── src/
│   ├── pom.xml
│   ├── mvnw
│   └── Dockerfile
│
├── gateway/
│   ├── src/
│   ├── pom.xml
│   ├── mvnw
│   └── Dockerfile
│
├── user-service/
│   ├── src/
│   ├── pom.xml
│   ├── mvnw
│   └── Dockerfile
│
├── product-service/
│   ├── src/
│   ├── pom.xml
│   ├── mvnw
│   └── Dockerfile
│
├── media-service/
│   ├── src/
│   ├── pom.xml
│   ├── mvnw
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── package-lock.json
│   ├── nginx.conf
│   └── Dockerfile
│
├── docker/
│   └── mongo/
│       └── init-mongo.js
│
├── certs/
│
├── Jenkinsfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

# Environment Configuration

Sensitive configuration must **not** be committed to Git.

The repository contains:

```text
.env.example
```

Create your local file:

```bash
cp .env.example .env
```

Then configure the required values.

Example:

```env
MONGO_ROOT_USERNAME=
MONGO_ROOT_PASSWORD=

USER_MONGO_DATABASE=
USER_MONGO_USERNAME=
USER_MONGO_PASSWORD=

PRODUCT_MONGO_DATABASE=
PRODUCT_MONGO_USERNAME=
PRODUCT_MONGO_PASSWORD=

MEDIA_MONGO_DATABASE=
MEDIA_MONGO_USERNAME=
MEDIA_MONGO_PASSWORD=

JWT_SECRET=
JWT_EXPIRATION=

SERVER_SSL_KEY_STORE_PASSWORD=

CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
```

Never commit the real `.env` file.

```text
.env.example   ✅ Git
.env           ❌ Git
```

---

# Docker Images

Application compilation is performed before the Docker runtime image is created.

For Spring Boot services:

```text
Source Code
    ↓
Maven Test
    ↓
Maven Package
    ↓
JAR Artifact
    ↓
Docker Image
```

The runtime Docker images contain the packaged application and the required runtime instead of rebuilding the application again.

Example backend Docker image:

```dockerfile
FROM eclipse-temurin:17-jre-alpine

WORKDIR /app

COPY target/*.jar app.jar

EXPOSE 8082

ENTRYPOINT ["java", "-jar", "app.jar"]
```

For Angular:

```text
Angular Source
      ↓
npm ci
      ↓
Tests
      ↓
ng build
      ↓
dist/frontend/browser
      ↓
Nginx Docker Image
```

Example frontend runtime image:

```dockerfile
FROM nginx:alpine

COPY dist/frontend/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

---

# Versioned Docker Images

Jenkins uses its build number as the application release tag.

For example, Jenkins build `25` creates:

```text
discovery:25
gateway:25
user-service:25
product-service:25
media-service:25
frontend:25
```

Docker Compose receives the version through:

```text
APP_IMAGE_TAG
```

Example:

```bash
APP_IMAGE_TAG=25 docker compose --env-file .env up -d
```

This is preferred over relying only on:

```text
latest
```

because every deployed release has an identifiable version.

It also makes rollback possible:

```text
Release 25 ❌

Rollback:

APP_IMAGE_TAG=24
```

---

# Running the Application

## Prerequisites

Make sure the following are available:

```text
Docker
Docker Compose
Git
```

For running the services outside Docker:

```text
Java 17+
Node.js 22+
npm
```

---

## Build Application Artifacts Manually

### Backend

Example:

```bash
cd product-service

./mvnw test
./mvnw package -DskipTests
```

The JAR is generated under:

```text
target/
```

Repeat the process for:

```text
user-service/
media-service/
gateway/
discovery/
```

---

## Frontend

```bash
cd frontend

npm ci
CI=true npm test -- --no-watch --no-progress
npm run build
```

The Angular production artifact is generated under:

```text
frontend/dist/frontend/browser/
```

---

## Build Docker Images Manually

Choose a common application tag:

```bash
export APP_IMAGE_TAG=local
```

Build the backend images:

```bash
docker build -t product-service:${APP_IMAGE_TAG} product-service
docker build -t user-service:${APP_IMAGE_TAG} user-service
docker build -t media-service:${APP_IMAGE_TAG} media-service
docker build -t gateway:${APP_IMAGE_TAG} gateway
docker build -t discovery:${APP_IMAGE_TAG} discovery
```

Build the frontend:

```bash
docker build -t frontend:${APP_IMAGE_TAG} frontend
```

Verify:

```bash
docker image ls
```

---

## Start the Platform

```bash
APP_IMAGE_TAG=local \
docker compose --env-file .env up -d
```

Check running containers:

```bash
docker compose ps
```

Stop the platform:

```bash
docker compose down
```

Do not use:

```bash
docker compose down -v
```

unless you intentionally want to remove persistent database volumes.

---

# Service Health

Every service in the main Docker Compose stack has a health check:

| Services | Check |
|---|---|
| Product, media, and user MongoDB | Authenticated MongoDB ping |
| Kafka | Broker responds to a topic-list request |
| Discovery, gateway, user, product, and media services | `/actuator/health` returns a successful HTTP response |
| Frontend | Nginx serves `/index.html` over HTTPS |

Gateway and frontend probes use HTTPS with certificate verification disabled for the local certificate. Backend probes run inside their containers; no additional host ports are needed. The frontend waits for the gateway to become healthy before starting.

The separate Jenkins stack checks the Docker daemon with `docker info` and Jenkins through `/login`. The standalone media MongoDB stack also has an authenticated ping check.

Start the platform and wait for all services to become healthy:

```bash
APP_IMAGE_TAG=local docker compose --env-file .env up -d --wait --wait-timeout 240
```

Inspect container health:

```bash
APP_IMAGE_TAG=local docker compose ps
```

Health checks report failures through Docker's `unhealthy` status; they do not automatically restart unhealthy containers.

---

# API Gateway

The API Gateway is the main backend entry point.

Responsibilities include:

```text
JWT verification
Request routing
CORS
User identity forwarding
Role propagation
```

Application services are not intended to be directly exposed to frontend clients.

The normal request flow is:

```text
Angular
   ↓
API Gateway
   ↓
JWT validation
   ↓
Eureka lookup
   ↓
Target Microservice
```

---

# Authentication

The User Service is responsible for:

```text
Registration
Login
JWT generation
Profile management
```

The Gateway validates the JWT before protected requests are forwarded.

Important authentication environment variables:

```env
JWT_SECRET=
JWT_EXPIRATION=
```

---

# API Routes

## Authentication

```http
POST /auth/register
POST /auth/login
```

---

## User Profile

```http
GET /me
PUT /me
```

Protected routes require:

```http
Authorization: Bearer <token>
```

---

## Products

```http
GET    /products
GET    /products/{id}

POST   /products
PUT    /products/{id}
DELETE /products/{id}

GET    /products/myshiit

PUT    /products/{id}/images
```

Product modification operations enforce seller role and ownership rules.

---

## Media

```http
POST /media/images
GET  /media/images/{id}
```

Media uploads are validated before being accepted.

Cloudinary configuration is provided through environment variables.

---

# Kafka

Kafka runs as a single-node KRaft broker.

Application containers connect internally using:

```text
kafka:9092
```

Current application events include:

| Topic | Producer | Event |
|---|---|---|
| `IMAGE_UPLOADED` | Media Service | Image successfully uploaded |
| `PRODUCT_CREATED` | Product Service | Product successfully created |

List Kafka topics:

```bash
docker compose exec kafka \
  kafka-topics \
  --bootstrap-server localhost:9092 \
  --list
```

Consume image events:

```bash
docker compose exec kafka \
  kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic IMAGE_UPLOADED \
  --from-beginning
```

Consume product events:

```bash
docker compose exec kafka \
  kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic PRODUCT_CREATED \
  --from-beginning
```

---

# Database Isolation

Each business service has its own MongoDB database.

```text
User Service
    ↓
User MongoDB

Product Service
    ↓
Product MongoDB

Media Service
    ↓
Media MongoDB
```

The Docker networks are separated:

```text
user-db-network
product-db-network
media-db-network
```

For example:

```text
Product Service
    ↓
product-db-network
    ↓
Product MongoDB
```

The Product Service does not need network access to the User or Media databases.

---

# Jenkins CI

Jenkins automates the Continuous Integration workflow.

The current pipeline follows this general flow:

```text
Git Repository
      ↓
Checkout
      ↓
Docker Environment Check
      ↓
Backend Tests
      ↓
Backend Packaging
      ↓
Frontend Tests
      ↓
Frontend Build
      ↓
Docker Image Build
      ↓
Docker Compose Validation
```

---

## Backend CI

Jenkins tests all Spring Boot services:

```text
Product Service
User Service
Media Service
API Gateway
Discovery Service
```

Tests are executed with:

```bash
./mvnw test
```

If a test fails, Jenkins receives a non-zero exit code.

Example:

```text
Product Tests     ✅
User Tests        ✅
Media Tests       ❌
Gateway Tests     SKIPPED
Package           SKIPPED
Docker Build      SKIPPED

Pipeline          FAILED
```

This prevents known broken code from moving further through the pipeline.

---

## Backend Packaging

After tests succeed:

```bash
./mvnw package -DskipTests
```

Tests are skipped during packaging because they were already executed in the previous CI stage.

The resulting JAR files are stored in:

```text
<service>/target/
```

---

# Frontend CI

Jenkins installs frontend dependencies using:

```bash
npm ci
```

`npm ci` uses the versions recorded in `package-lock.json`, making CI builds reproducible.

Tests run with:

```bash
CI=true npm test -- --no-watch --no-progress
```

The Angular build is then generated using:

```bash
npm run build
```

If tests fail, the frontend build stage does not continue.

---

# Jenkins Docker Architecture

Jenkins itself runs inside Docker.

The custom Jenkins image includes:

```text
Jenkins
Java
Docker CLI
Docker Compose plugin
Node.js
npm
```

Jenkins communicates with a dedicated Docker daemon running through Docker-in-Docker.

```text
Host Machine
│
├── Jenkins Container
│      │
│      ├── Jenkins
│      ├── Java
│      ├── Node.js
│      └── Docker CLI
│               │
│               ▼
│
└── Jenkins Docker Daemon
       │
       ├── Builds application images
       └── Runs CI containers
```

The Docker CLI sends commands.

The Docker daemon performs the actual Docker operations.

---

# Jenkins Persistence

Jenkins configuration is stored in a Docker volume:

```text
jenkins_home
```

This contains information such as:

```text
Jobs
Plugins
Users
Credentials metadata
Build history
Configuration
Workspaces
```

Running:

```bash
docker compose down
```

does not remove the volume.

Therefore Jenkins configuration survives container recreation.

Avoid:

```bash
docker compose down -v
```

unless deleting Jenkins data is intentional.

---

# Jenkins Setup

Start Jenkins:

```bash
cd jenkins-lab

docker compose up -d --build
```

Open:

```text
http://localhost:8085
```

Verify Docker access from Jenkins:

```bash
docker exec jenkins docker version
```

The result should contain both:

```text
Client
Server
```

Verify Node.js:

```bash
docker exec jenkins node --version
docker exec jenkins npm --version
```

---

# Jenkins Credentials

Secrets must not be stored directly inside:

```text
Jenkinsfile
docker-compose.yml
Git repository
```

The real environment file is stored inside the Jenkins Credentials Store as a:

```text
Secret file
```

Credential ID:

```text
buy01-env
```

The pipeline accesses it temporarily using Jenkins credentials binding.

Conceptually:

```text
Jenkins Credentials Store
          ↓
       buy01-env
          ↓
      Pipeline
          ↓
 Docker Compose
```

The pipeline must never print the file using commands such as:

```bash
cat "$ENV_FILE"
```

because secrets could appear in Jenkins build logs.

---

# Docker Compose Validation

Before deployment, Jenkins validates the Compose configuration.

Conceptually:

```bash
APP_IMAGE_TAG=${BUILD_NUMBER} \
docker compose \
  --env-file "$ENV_FILE" \
  config
```

The resolved configuration output should not be printed in CI logs because it may contain sensitive environment values.

---

# Pipeline Versioning

Each successful Jenkins build represents a potential application release.

Example:

```text
Jenkins Build #42
```

produces:

```text
discovery:42
gateway:42
user-service:42
product-service:42
media-service:42
frontend:42
```

This makes the relationship clear:

```text
Git Commit
   ↓
Jenkins Build
   ↓
Docker Release
```

---

# CI Failure Strategy

The Jenkins pipeline follows a **fail-fast** strategy.

If an important command returns a non-zero exit code:

```text
Current Stage  → FAILED
Pipeline       → FAILED
Later Stages   → SKIPPED
```

Deployment must never happen when tests or builds are failing.

---

# Continuous Deployment — Next Steps

The CI portion currently covers:

```text
Checkout
Tests
Package
Frontend Build
Docker Images
Compose Validation
```

The next CD steps are:

```text
Docker Compose Deployment
        ↓
Health Check
        ↓
Application Healthy?
       /       \
     YES        NO
      ↓          ↓
 Success      Rollback
      ↓
Notification
```

The final pipeline will also include:

- automatic deployment
- post-deployment health verification
- rollback to the previous working release
- success/failure notifications
- automatic GitHub webhook triggering

---

# Planned Rollback Strategy

Because Docker images use Jenkins build numbers, rollback can return to the previous release.

Example:

```text
Release 41 ✅
Release 42 ❌
```

If release `42` fails its health checks:

```text
APP_IMAGE_TAG=41
```

can be used to restore the previous working application images.

Rollback will be automated as part of the CD pipeline.

---

# GitHub Integration

The Jenkins Pipeline is stored as code in:

```text
Jenkinsfile
```

The Jenkins Job uses:

```text
Pipeline script from SCM
SCM: Git
```

The repository contains the Jenkins pipeline definition, which allows CI configuration to be version-controlled together with the application.

The intended final flow is:

```text
Developer
   ↓
git push
   ↓
GitHub
   ↓
Webhook
   ↓
Jenkins
   ↓
Checkout
   ↓
Test
   ↓
Build
   ↓
Deploy
```

---

# Security Practices

The project follows several basic security practices:

- JWT authentication at the API Gateway
- seller ownership validation
- service-specific databases
- private Docker database networks
- non-root application containers where applicable
- secrets outside Git
- Jenkins Credentials Store
- versioned Docker releases
- health checks before accepting deployments
- HTTPS for the frontend and API Gateway

---

# Useful Commands

Check running containers:

```bash
docker ps
```

Check Compose services:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f
```

View one service:

```bash
docker compose logs -f product-service
```

Check Docker images:

```bash
docker image ls
```

Check a versioned image:

```bash
docker image inspect product-service:25
```

Run backend tests:

```bash
./mvnw test
```

Package backend:

```bash
./mvnw package -DskipTests
```

Install frontend dependencies:

```bash
npm ci
```

Run frontend tests:

```bash
CI=true npm test -- --no-watch --no-progress
```

Build frontend:

```bash
npm run build
```

---

# Current Project Status

### Application

- [x] Eureka Service Discovery
- [x] API Gateway
- [x] JWT authentication
- [x] User Service
- [x] Product Service
- [x] Media Service
- [x] MongoDB per service
- [x] Kafka integration
- [x] Angular frontend
- [x] Dockerized services
- [x] HTTPS configuration

### Jenkins CI

- [x] Jenkins running in Docker
- [x] Persistent Jenkins volume
- [x] Git repository integration
- [x] Backend automated tests
- [x] Backend packaging
- [x] Frontend dependency installation
- [x] Frontend automated tests
- [x] Angular production build
- [x] Versioned Docker images
- [x] Jenkins secret file credentials
- [x] Docker Compose validation

### CD

- [ ] Automatic deployment
- [ ] Post-deployment health checks
- [ ] Automatic rollback
- [ ] Build notifications
- [ ] GitHub webhook trigger

### Bonus

- [ ] Parameterized deployments
- [ ] Parallel CI stages
- [ ] Distributed Jenkins agents

---

# Contributors

Developed as part of a microservices and DevOps learning project focused on:

```text
Spring Boot
Angular
Microservices
Docker
Kafka
Jenkins
CI/CD
```