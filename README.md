# MR-Jenk — Automated CI/CD Pipeline with Jenkins

> Production-grade Continuous Integration & Continuous Deployment (CI/CD) pipeline for an e-commerce microservices platform using **Jenkins**, **Docker-in-Docker (DinD)**, **Jenkins Configuration as Code (JCasC)**, and **GitHub Webhooks**.

---

## 📋 Table of Contents

- [Overview & Objectives](#-overview--objectives)
- [Pipeline Architecture](#-pipeline-architecture)
- [⚡ Quick Start: Run the Project in 5 Minutes](#-quick-start-run-the-project-in-5-minutes)
  - [1. Prerequisites](#1-prerequisites)
  - [2. Configure Secrets](#2-configure-secrets)
  - [3. Start Jenkins Infrastructure](#3-start-jenkins-infrastructure)
  - [4. Expose Webhook via Ngrok](#4-expose-webhook-via-ngrok)
  - [5. Run the Pipeline](#5-run-the-pipeline)
  - [6. Verify Deployment](#6-verify-deployment)
- [🛡️ Key Pipeline Features](#️-key-pipeline-features)
  - [Automated Testing & JUnit Reporting](#automated-testing--junit-reporting)
  - [Protected Deployment Branch (`main` only)](#protected-deployment-branch-main-only)
  - [Automatic Rollback Mechanism](#automatic-rollback-mechanism)
  - [Security & Credentials Management](#security--credentials-management)
- [🧪 Evaluation & Defense Guide](#-evaluation--defense-guide)
  - [How to Demonstrate Intentional Failure & Rollback](#how-to-demonstrate-intentional-failure--rollback)
  - [Audit Checklist Answers](#audit-checklist-answers)

---

## 🎯 Overview & Objectives

In this project, you act as a **DevOps Engineer** responsible for automating the end-to-end development, testing, and deployment lifecycle of a containerized microservices application.

### Key Objectives:
- **Automation**: Code is automatically fetched and built upon push events via GitHub Webhooks.
- **Automated Testing**: Dedicated stages run JUnit 5 tests for all backend services and test runners for Angular.
- **Fail-Fast CI**: Pipeline immediately aborts if any test, compile, or build step fails.
- **Continuous Deployment (CD)**: Automatically deploys 10 containers to an isolated Docker-in-Docker daemon using Docker Compose with versioned image tags (`${BUILD_NUMBER}`).
- **Branch Protection**: Deployment is restricted exclusively to the `main` branch.
- **Zero-Downtime Rollback**: Automatically reverts to the last known healthy release if post-deployment health checks fail.
- **Notifications & Reporting**: Publishes interactive JUnit test reports and sends build status notifications.

---

## 🏗️ Pipeline Architecture

```text
GitHub Push Event
       │
       ▼
GitHub Webhook (Ngrok Tunnel)
       │
       ▼
Jenkins Controller (Port 8085)
       │
┌──────┴────────────────────────────────────────────────┐
│  CONTINUOUS INTEGRATION (CI)                          │
│                                                       │
│  [Docker Check] ──► [Product Service Tests] (JUnit)   │
│                 ──► [User Service Tests] (JUnit)      │
│                 ──► [Media Service Tests] (JUnit)     │
│                 ──► [Gateway Tests] (JUnit)           │
│                 ──► [Discovery Tests] (JUnit)         │
│                 ──► [Package Backend JARs]            │
│                 ──► [Frontend CI] (Tests + Build)     │
│                 ──► [Build Versioned Docker Images]   │
│                 ──► [Verify Images Exist]             │
└──────┬────────────────────────────────────────────────┘
       │
       ▼
┌───────────────────────────────────────────────────────┐
│  CONTINUOUS DEPLOYMENT (CD) — (main branch only)      │
│                                                       │
│  [Prepare TLS Certificates]                           │
│       │                                               │
│  [Validate Docker Compose]                            │
│       │                                               │
│  [Deploy Containers to DinD]                          │
│       │                                               │
│  [Post-Deployment Health Checks (10 Containers)]      │
│       │                                               │
│       ├──► Healthy? ──► YES ──► Save Release #        │
│       │                                               │
│       └──► Healthy? ──► NO  ──► AUTOMATIC ROLLBACK    │
│                                 (Restores previous #) │
└──────┬────────────────────────────────────────────────┘
       │
       ▼
[Post Actions: JUnit Reports Archive + Email / Banner Notifications]
```

---

## ⚡ Quick Start: Run the Project in 5 Minutes

### 1. Prerequisites

Ensure you have installed:
- **Docker** & **Docker Compose** (v2+)
- **Git**
- **Ngrok** (or use the binary included in `jenkins-lab/ngrok`)

---

### 2. Configure Secrets

From the project root, create the secrets folder mounted into Jenkins:

```bash
mkdir -p jenkins-lab/jenkins-secrets
chmod 700 jenkins-lab/jenkins-secrets
```

Create the text credentials and secret files:

```bash
# 1. Admin password for Jenkins UI
echo "admin123" > jenkins-lab/jenkins-secrets/jenkins-admin-password

# 2. Your GitHub username
echo "YOUR_GITHUB_USERNAME" > jenkins-lab/jenkins-secrets/github-username

# 3. Your GitHub Personal Access Token (repo scope)
echo "ghp_your_github_token" > jenkins-lab/jenkins-secrets/github-pat

# 4. Copy the environment configuration
cp .env.example jenkins-lab/jenkins-secrets/buy01-env

# 5. Generate TLS Certificates (or copy from certs/ if already generated)
# Generate private key and certificate:
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout jenkins-lab/jenkins-secrets/gateway-keystore.key \
  -out jenkins-lab/jenkins-secrets/gateway-keystore.crt \
  -subj "/CN=localhost"

# Generate PKCS12 keystore for API Gateway:
openssl pkcs12 -export \
  -in jenkins-lab/jenkins-secrets/gateway-keystore.crt \
  -inkey jenkins-lab/jenkins-secrets/gateway-keystore.key \
  -out jenkins-lab/jenkins-secrets/gateway-keystore.p12 \
  -name gateway \
  -password pass:changeit

# (Note: If you already have existing certs: cp certs/gateway-keystore.* jenkins-lab/jenkins-secrets/)
```

Set secure permissions for the mounted secret files. The Jenkins entrypoint reads
them as root, exports the required values, and then starts Jenkins as UID `1000`:

```bash
chmod 750 jenkins-lab/jenkins-secrets
chmod 640 jenkins-lab/jenkins-secrets/*
```

---

### 3. Start Jenkins Infrastructure

Start the Jenkins controller and Docker-in-Docker daemon:

```bash
cd jenkins-lab
docker compose up -d --build
cd ..
```

- **Jenkins Controller UI**: [http://localhost:8085](http://localhost:8085)
- **Login**: `admin` / your password (e.g. `admin123`)
- **Job Status**: The `first-pipeline` job is provisioned automatically via JCasC.

---

### 4. Expose Webhook via Ngrok

In a separate terminal, run ngrok with your domain:

```bash
./ngrok http 8085 --url https://vowel-audio-diner.ngrok-free.dev
# or from inside jenkins-lab/:
# ./ngrok http 8085 --url https://vowel-audio-diner.ngrok-free.dev
```

Configure the Webhook in GitHub:
1. Go to your GitHub repository: **Settings ➔ Webhooks ➔ Add webhook**.
2. **Payload URL**: `https://vowel-audio-diner.ngrok-free.dev/github-webhook/` *(Notice the trailing slash!)*.
3. **Content type**: `application/json`.
4. **SSL verification**: Enable.
5. **Which events**: `Just the push event`.
6. Click **Add webhook**.

---

### 5. Run the Pipeline

#### Automatic Trigger:
Push any commit to the `main` branch:
```bash
git commit -am "chore: trigger build"
git push origin main
```
Jenkins will instantly start the build.

#### Manual Trigger:
Open [http://localhost:8085/job/first-pipeline/](http://localhost:8085/job/first-pipeline/) and click **Build Now**.

---

### 6. Verify Deployment

When the build finishes with **PIPELINE SUCCESS**, verify the 10 deployed microservices:

```bash
docker exec jenkins-docker docker ps
```

All 10 containers will show `Up ... (healthy)`:
- `buy01-frontend` (Angular served via Nginx on `https://localhost:4200`)
- `buy01-gateway` (Spring Cloud Gateway on `https://localhost:8444`)
- `buy01-discovery` (Eureka Service Discovery)
- `buy01-user-service`
- `buy01-product-service`
- `buy01-media-service`
- `buy01-kafka`
- `product-mongodb`, `user-mongodb`, `media-mongodb`

---

## 🛡️ Key Pipeline Features

### Automated Testing & JUnit Reporting
- Every backend microservice runs its test suite (`./mvnw test`) in an isolated stage.
- Frontend runs automated Karma / Vitest tests (`npm test`).
- Test results are automatically collected via `junit testResults: '**/target/surefire-reports/*.xml'` in `post { always { ... } }`, generating interactive trend charts directly in Jenkins.

### Protected Deployment Branch (`main` only)
Deployment stages are guarded by Declarative branch directives:
```groovy
stage('Deploy') {
    when {
        branch 'main'
    }
    steps { ... }
}
```
When developers push feature or bugfix branches, full CI (tests and Docker image builds) runs to validate code quality, but deployment is skipped.

### Automatic Rollback Mechanism
The pipeline tracks the last successful release number in:
`/var/jenkins_home/deploy-secrets/buy01/last-successful-release`

1. **New Release Deployment**: Release `${BUILD_NUMBER}` is deployed and health-checked.
2. **Success**: If all 10 containers are healthy, `${BUILD_NUMBER}` is stored as the new fallback release.
3. **Failure**: If any container fails its health checks:
   - The pipeline reads the previous release number from `last-successful-release`.
   - Runs `APP_IMAGE_TAG=$PREVIOUS_RELEASE docker compose up -d`.
   - Verifies the rollback containers are healthy.
   - Exits with error code `1` to mark the Jenkins build as `FAILED`, while keeping production online.

### Security & Credentials Management
- **No hardcoded secrets**: All API keys, passwords, and tokens are stored in Jenkins Credentials Store via JCasC (`jenkins-lab/jcasc/jenkins.yaml`).
- **Log masking**: Pipeline commands using credentials employ `set +x` to prevent sensitive tokens from leaking into console logs.
- **Strict Role Isolation**: Anonymous users have read-only access for webhook triggering; administrative modifications require full authentication.

---

## 🧪 Evaluation & Defense Guide

### How to Demonstrate Intentional Failure & Rollback

To prove that the pipeline halts on errors and triggers automatic rollback:

1. **Simulate a broken unit test**:
   In `product-service/src/test/java/com/buy01/product_service/controller/ProductControllerTest.java`, change an assertion to fail (e.g. `assertEquals(200, 500)`).
2. **Push the change**:
   ```bash
   git commit -am "test: intentional test failure"
   git push origin main
   ```
3. **Observe Jenkins**:
   - The build stops immediately at `Product Service Tests`.
   - The build turns **RED (FAILED)**.
   - Deployment is **never** executed, protecting production.
4. **Revert the change**:
   ```bash
   git revert HEAD
   git push origin main
   ```
   Jenkins rebuilds and restores green status.

---

### Audit Checklist Answers

| Audit Item | Answer / Verification |
|---|---|
| **Pipeline runs start to finish?** | **YES**: Fully automated from checkout, tests, builds to deployment. |
| **Responds to build errors?** | **YES**: Stops immediately on test or compile failure; triggers rollback on deployment failure. |
| **Tests run automatically?** | **YES**: 5x JUnit backend suites + Angular frontend test suite. |
| **New commit triggers build?** | **YES**: GitHub Webhook via Ngrok triggers builds on git push. |
| **Automatic deployment & rollback?** | **YES**: Docker Compose deployments with `${BUILD_NUMBER}` + automatic rollback. |
| **Permissions appropriately set?** | **YES**: JCasC restricts signup and admin access; anonymous read-only. |
| **Sensitive data secured?** | **YES**: Stored in Jenkins Credentials Store and mounted via `/run/secrets`. |
| **Test reports stored?** | **YES**: Maven Surefire XMLs published to Jenkins JUnit Test Result dashboard. |
| **Notifications configured?** | **YES**: Detailed console log banners and email notifications in `post` blocks. |

