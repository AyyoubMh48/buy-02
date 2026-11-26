pipeline {
    agent any
    options {
        // Prevent two deployments from running at the same time
        disableConcurrentBuilds()
    }
    triggers {
        // Triggers the build instantly when GitHub sends a webhook push event
        githubPush()
        cron('H H(1-4) * * *')
    }
    environment {
        BRANCH_NAME = "${env.GIT_BRANCH ? env.GIT_BRANCH.replace('origin/', '') : 'main'}"
        // Read-only Nexus credentials apply to dependency/plugin resolution in every Maven stage.
        NEXUS_URL = credentials('nexus-url')
        NEXUS_READER = credentials('nexus-maven-reader')
        NEXUS_READ_USERNAME = "${NEXUS_READER_USR}"
        NEXUS_READ_PASSWORD = "${NEXUS_READER_PSW}"
        NEXUS_CA_BUNDLE = credentials('nexus-ca')
        NEXUS_JAVA_TRUSTSTORE = credentials('nexus-java-truststore')
        JAVA_TOOL_OPTIONS = "-Djavax.net.ssl.trustStore=\"${NEXUS_JAVA_TRUSTSTORE}\" -Djavax.net.ssl.trustStorePassword=changeit"
    }
    stages {
        // ========================================
        // 1. Docker Environment Check
        // ========================================
        stage('Docker Check') {
            steps {
                sh 'docker version'
            }
        }

        // ========================================
        // 2. Backend Tests
        // ========================================
        stage('Product Service Tests') {
            steps {
                dir('product-service') {
                    sh 'bash ./mvnw -s "$WORKSPACE/nexus/maven/settings.xml" -B clean test'
                }
            }
        }

        stage('User Service Tests') {
            steps {
                dir('user-service') {
                    sh 'bash ./mvnw -s "$WORKSPACE/nexus/maven/settings.xml" -B clean test'
                }
            }
        }

        stage('Media Service Tests') {
            steps {
                dir('media-service') {
                    sh 'bash ./mvnw -s "$WORKSPACE/nexus/maven/settings.xml" -B clean test'
                }
            }
        }

        stage('Order Service Tests') {
            steps {
                dir('order-service') {
                    sh 'bash ./mvnw -s "$WORKSPACE/nexus/maven/settings.xml" -B clean test'
                }
            }
        }

        stage('Gateway Tests') {
            steps {
                withCredentials([
                    file(
                        credentialsId: 'buy01-env',
                        variable: 'ENV_FILE'
                    )
                ]) {
                    dir('gateway') {
                        sh '''
                            set +x
                            set -a
                            . "$ENV_FILE"
                            set +a
                            bash ./mvnw -s "$WORKSPACE/nexus/maven/settings.xml" -B clean test
                        '''
                    }
                }
            }
        }

        stage('Discovery Tests') {
            steps {
                dir('discovery') {
                    sh 'bash ./mvnw -s "$WORKSPACE/nexus/maven/settings.xml" -B clean test'
                }
            }
        }

        stage('Frontend Tests') {
            steps {
                dir('frontend') {
                    sh 'npm ci'
                    sh 'CI=true npm run test:coverage'
                }
            }
        }

        // ========================================
        // 3. Package Backend + JaCoCo XML report
        // ========================================
        // Tests already ran. No clean here: preserve target/jacoco.exec.
        stage('Package Backend') {
            steps {
                dir('product-service') {
                    sh 'bash ./mvnw -s "$WORKSPACE/nexus/maven/settings.xml" -B verify -DskipTests'
                }
                dir('user-service') {
                    sh 'bash ./mvnw -s "$WORKSPACE/nexus/maven/settings.xml" -B verify -DskipTests'
                }
                dir('media-service') {
                    sh 'bash ./mvnw -s "$WORKSPACE/nexus/maven/settings.xml" -B verify -DskipTests'
                }
                dir('order-service') {
                    sh 'bash ./mvnw -s "$WORKSPACE/nexus/maven/settings.xml" -B verify -DskipTests'
                }
                withCredentials([file(credentialsId: 'buy01-env', variable: 'ENV_FILE')]) {
                    dir('gateway') {
                        sh '''
                            set +x
                            set -a
                            . "$ENV_FILE"
                            set +a
                            bash ./mvnw -s "$WORKSPACE/nexus/maven/settings.xml" -B verify -DskipTests
                        '''
                    }
                }
                dir('discovery') {
                    sh 'bash ./mvnw -s "$WORKSPACE/nexus/maven/settings.xml" -B verify -DskipTests'
                }
            }
        }

        // ========================================
        // 4. Check Backend Artifacts
        // ========================================
        stage('Check Backend Artifacts') {
            steps {
                sh 'python3 scripts/nexus/images.py check-jars'
            }
        }

        // ========================================
        // 5. Frontend CI
        // ========================================
        stage('Package Frontend') {
            steps {
                dir('frontend') {
                    sh 'npm run build'
                    sh 'ls -la dist/frontend/browser'
                }
            }
        }

        // ========================================
        // 6. SonarQube Analysis and Quality Gates
        // ========================================
        stage('Coverage') {
            steps {
                sh '''
                    for component in product-service user-service media-service order-service gateway discovery; do
                        test -s "$component/target/site/jacoco/jacoco.xml"
                    done
                    test -s frontend/coverage/frontend/lcov.info
                '''
            }
        }
        stage('SonarQube analyses and Quality Gates') {
            steps {
                script {
                    if (env.BRANCH_NAME != 'main') {
                        error('Community Build analysis is restricted to main')
                    }
                    def components = [
                        ['product-service', 'product', 'buy01-product-service'],
                        ['user-service', 'user', 'buy01-user-service'],
                        ['media-service', 'media', 'buy01-media-service'],
                        ['order-service', 'order', 'buy01-order-service'],
                        ['gateway', 'gateway', 'buy01-gateway'],
                        ['discovery', 'discovery', 'buy01-discovery'],
                        ['frontend', 'frontend', 'buy01-frontend']
                    ]
                    // Consume each CE task before submitting the next analysis.
                    for (component in components) {
                        def credential = "sonar-${component[1]}-token"
                        def projectKey = env.getProperty("SONAR_${component[1].toUpperCase()}_PROJECT_KEY")
                        if (!projectKey?.trim()) {
                            error("Missing exact SonarQube project key for ${component[1]}; run sonar-init and restart Jenkins")
                        }
                        dir(component[0]) {
                            withSonarQubeEnv(installationName: 'SonarQube', credentialsId: credential) {
                                withCredentials([string(credentialsId: credential, variable: 'SONAR_TOKEN')]) {
                                    withEnv(["SONAR_PROJECT_KEY=${projectKey}"]) {
                                        if (component[0] == 'frontend') {
                                            sh '''
                                                set +x
                                                test -s coverage/frontend/lcov.info
                                                sonar-scanner -Dsonar.projectKey="$SONAR_PROJECT_KEY"
                                            '''
                                        } else {
                                            sh '''
                                                set +x
                                                test -s target/site/jacoco/jacoco.xml
                                                bash ./mvnw -s "$WORKSPACE/nexus/maven/settings.xml" -B org.sonarsource.scanner.maven:sonar-maven-plugin:5.8.0.7211:sonar \\
                                                  -Dsonar.projectKey="$SONAR_PROJECT_KEY" \\
                                                  -Dsonar.coverage.jacoco.xmlReportPaths=target/site/jacoco/jacoco.xml
                                            '''
                                        }
                                    }
                                }
                            }
                            timeout(time: 10, unit: 'MINUTES') {
                                try {
                                    def gate = waitForQualityGate(credentialsId: credential, abortPipeline: true)
                                    if (gate.status != 'OK') {
                                        error("Quality Gate failed for ${projectKey}: ${gate.status}")
                                    }
                                } catch (Exception failure) {
                                    withCredentials([string(credentialsId: credential, variable: 'SONAR_TOKEN')]) {
                                        withEnv(["SONAR_PROJECT_KEY=${projectKey}", 'SONAR_HOST_URL=http://sonarqube:9000']) {
                                            sh(script: 'set +x; node ../jenkins-lab/sonar-init/quality-gate.js', returnStatus: true)
                                        }
                                    }
                                    throw failure
                                }
                            }
                        }
                    }
                }
            }
        }
        stage('Publish Maven Artifacts to Nexus') {
            when {
                expression { env.BRANCH_NAME == 'main' && !env.CHANGE_ID && !currentBuild.getBuildCauses('hudson.triggers.TimerTrigger$TimerTriggerCause') }
            }
            steps {
                withCredentials([
                    usernamePassword(credentialsId: 'nexus-maven-publisher', usernameVariable: 'NEXUS_PUBLISH_USERNAME', passwordVariable: 'NEXUS_PUBLISH_PASSWORD')
                ]) {
                    sh(script: '''
                        set +x
                        set -eu
                        export PYTHONPATH="$WORKSPACE/scripts/nexus"

                        # Check every local input and reject existing releases before uploading.
                        publish_plan=$(python3 - <<'PY'
                        from pathlib import Path
                        from xml.etree import ElementTree as ET

                        from nexus_api import Client, artifact_directory

                        publisher = Client('NEXUS_PUBLISH')
                        Client('NEXUS_READ')
                        ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
                        services = ('discovery', 'gateway', 'user-service', 'product-service',
                                    'media-service', 'order-service')
                        for service in services:
                            pom = Path(service) / 'pom.xml'
                            if not pom.is_file():
                                raise SystemExit(f'Missing project POM: {pom}')
                            project = ET.parse(pom).getroot()
                            group, artifact, version = (
                                project.findtext('m:' + key, default='', namespaces=ns).strip()
                                for key in ('groupId', 'artifactId', 'version')
                            )
                            directory = artifact_directory(group, artifact, version)
                            jar = Path(service) / 'target' / f'{artifact}-{version}.jar'
                            if not jar.is_file() or jar.stat().st_size == 0:
                                raise SystemExit(f'Missing or empty packaged JAR: {jar}')
                            snapshot = version.endswith('-SNAPSHOT')
                            repository = 'maven-snapshots' if snapshot else 'maven-releases'
                            server = 'nexus-snapshots' if snapshot else 'nexus-releases'
                            if not snapshot and publisher.exists(
                                f'/repository/{repository}/{directory}/{artifact}-{version}.pom'
                            ):
                                raise SystemExit(f'Release {group}:{artifact}:{version} already exists. Use a new version.')
                            print(service, group, artifact, version, repository, server)
                        PY
                        )
                        export NEXUS_URL="${NEXUS_URL%/}"

                        while read -r service group artifact version repository server; do
                            jar="$WORKSPACE/$service/target/$artifact-$version.jar"
                            pom="$WORKSPACE/$service/pom.xml"
                            (
                                cd "$service"
                                bash ./mvnw -B -ntp -s "$WORKSPACE/nexus/maven/settings.xml" \\
                                    org.apache.maven.plugins:maven-deploy-plugin:3.1.4:deploy-file \\
                                    -DrepositoryId="$server" -Durl="$NEXUS_URL/repository/$repository/" \\
                                    -DgroupId="$group" -DartifactId="$artifact" -Dversion="$version" \\
                                    -Dpackaging=jar -Dfile="$jar" -DpomFile="$pom" -DgeneratePom=false
                            )

                            # Fetch hosted snapshot metadata and compare fresh HTTP downloads.
                            python3 - "$group" "$artifact" "$version" "$repository" "$jar" "$pom" <<'PY'
                        import hashlib
                        import sys

                        from nexus_api import Client, artifact_paths

                        group, artifact, version, repository, jar, pom = sys.argv[1:]
                        publisher = Client('NEXUS_PUBLISH')
                        reader = Client('NEXUS_READ')
                        paths = artifact_paths(publisher, repository, group, artifact, version)
                        for extension, local_file in (('jar', jar), ('pom', pom)):
                            digest = hashlib.sha256()
                            with open(local_file, 'rb') as stream:
                                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                                    digest.update(chunk)
                            expected = digest.hexdigest()
                            hosted_path = paths[extension]
                            group_path = hosted_path.replace(f'/repository/{repository}/', '/repository/maven-public/', 1)
                            if publisher.digest(hosted_path) != expected:
                                raise SystemExit(f'Hosted {extension} checksum mismatch: {hosted_path}')
                            if reader.digest(group_path) != expected:
                                raise SystemExit(f'Reader {extension} checksum mismatch: {group_path}')
                            print(f'Verified {group}:{artifact}:{version} {extension} SHA-256 {expected}')
                        PY
                        done <<PLAN
                        $publish_plan
                        PLAN
                    '''.stripIndent(24))
                }
            }
        }

        // Image builds start only after all Quality Gates pass.
        stage('Build Product Image') {
            steps {
                dir('product-service') {
                    sh '''
                        docker build --load \\
                            -t product-service:${BUILD_NUMBER} \\
                            .
                    '''
                }
            }
        }

        stage('Build User Image') {
            steps {
                dir('user-service') {
                    sh '''
                        docker build --load \\
                            -t user-service:${BUILD_NUMBER} \\
                            .
                    '''
                }
            }
        }

        stage('Build Media Image') {
            steps {
                dir('media-service') {
                    sh '''
                        docker build --load \\
                            -t media-service:${BUILD_NUMBER} \\
                            .
                    '''
                }
            }
        }

        stage('Build Order Image') {
            steps {
                dir('order-service') {
                    sh '''
                        docker build --load \\
                            -t order-service:${BUILD_NUMBER} \\
                            .
                    '''
                }
            }
        }

        stage('Build Gateway Image') {
            steps {
                dir('gateway') {
                    sh '''
                        docker build --load \\
                            -t gateway:${BUILD_NUMBER} \\
                            .
                    '''
                }
            }
        }

        stage('Build Discovery Image') {
            steps {
                dir('discovery') {
                    sh '''
                        docker build --load \\
                            -t discovery:${BUILD_NUMBER} \\
                            .
                    '''
                }
            }
        }

        stage('Build Frontend Image') {
            steps {
                dir('frontend') {
                    sh '''
                        docker build --load \\
                            -t frontend:${BUILD_NUMBER} \\
                            .
                    '''
                }
            }
        }

        // ========================================
        // 7. Check Complete Release
        // ========================================
        stage('Check Docker Images') {
            steps {
                sh '''
                    echo "================================"
                    echo "Release #${BUILD_NUMBER}"
                    echo "================================"
                    docker image inspect product-service:${BUILD_NUMBER} > /dev/null
                    docker image inspect user-service:${BUILD_NUMBER} > /dev/null
                    docker image inspect media-service:${BUILD_NUMBER} > /dev/null
                    docker image inspect order-service:${BUILD_NUMBER} > /dev/null
                    docker image inspect gateway:${BUILD_NUMBER} > /dev/null
                    docker image inspect discovery:${BUILD_NUMBER} > /dev/null
                    docker image inspect frontend:${BUILD_NUMBER} > /dev/null
                    echo "All Docker images exist:"
                    echo "product-service:${BUILD_NUMBER}"
                    echo "user-service:${BUILD_NUMBER}"
                    echo "media-service:${BUILD_NUMBER}"
                    echo "order-service:${BUILD_NUMBER}"
                    echo "gateway:${BUILD_NUMBER}"
                    echo "discovery:${BUILD_NUMBER}"
                    echo "frontend:${BUILD_NUMBER}"
                '''
            }
        }

        // ========================================
        // 8. Prepare TLS Certificates
        // ========================================
        stage('Publish and Verify Nexus Images') {
            when {
                expression { env.BRANCH_NAME == 'main' && !env.CHANGE_ID && !currentBuild.getBuildCauses('hudson.triggers.TimerTrigger$TimerTriggerCause') }
            }
            steps {
                withCredentials([
                    string(credentialsId: 'nexus-docker-registry', variable: 'NEXUS_DOCKER_REGISTRY'),
                    usernamePassword(credentialsId: 'nexus-docker-publisher', usernameVariable: 'NEXUS_DOCKER_PUBLISH_USERNAME', passwordVariable: 'NEXUS_DOCKER_PUBLISH_PASSWORD'),
                    usernamePassword(credentialsId: 'nexus-docker-reader', usernameVariable: 'NEXUS_DOCKER_READ_USERNAME', passwordVariable: 'NEXUS_DOCKER_READ_PASSWORD')
                ]) {
                    sh '''
                        set +x
                        set -eu
                        release_tag=$(python3 scripts/nexus/images.py tag --build "$BUILD_NUMBER")
                        python3 scripts/nexus/images.py publish --source-tag "$BUILD_NUMBER" \
                            --tag "$release_tag" --include-frontend \
                            --manifest "reports/nexus/release-${BUILD_NUMBER}.json"
                    '''
                }
            }
        }

        stage('Prepare Deployment Files') {
            when {
                expression { env.BRANCH_NAME == 'main' && !env.CHANGE_ID && !currentBuild.getBuildCauses('hudson.triggers.TimerTrigger$TimerTriggerCause') }
            }
            steps {
                withCredentials([
                    file(
                        credentialsId: 'gateway-p12',
                        variable: 'P12_FILE'
                    ),
                    file(
                        credentialsId: 'gateway-crt',
                        variable: 'CRT_FILE'
                    ),
                    file(
                        credentialsId: 'gateway-key',
                        variable: 'KEY_FILE'
                    )
                ]) {
                    sh '''
                        set +x
                        CERT_DIR="/var/jenkins_home/deploy-secrets/${DEPLOY_PROJECT:-buy01}/certs"
                        mkdir -p "$CERT_DIR"
                        cp "$P12_FILE" \\
                           "$CERT_DIR/gateway-keystore.p12"
                        cp "$CRT_FILE" \\
                           "$CERT_DIR/gateway-keystore.crt"
                        cp "$KEY_FILE" \\
                           "$CERT_DIR/gateway-keystore.key"
                        chmod 600 \\
                            "$CERT_DIR/gateway-keystore.p12"
                        chmod 644 \\
                            "$CERT_DIR/gateway-keystore.crt"
                        chmod 600 \\
                            "$CERT_DIR/gateway-keystore.key"
                        if [ -n "${DEPLOY_CERT_VOLUME:-}" ]; then
                            docker volume create "$DEPLOY_CERT_VOLUME" > /dev/null
                            tar -C "$CERT_DIR" -cf - gateway-keystore.p12 gateway-keystore.crt gateway-keystore.key |
                                docker run --rm -i --network none --entrypoint tar \\
                                    -v "$DEPLOY_CERT_VOLUME:/certs" nginx:alpine \\
                                    --no-same-owner -xf - -C /certs
                        fi
                        if [ -n "${DEPLOY_MONGO_INIT_VOLUME:-}" ]; then
                            docker volume create "$DEPLOY_MONGO_INIT_VOLUME" > /dev/null
                            tar -C docker/mongo -cf - init-mongo.js |
                                docker run --rm -i --network none --entrypoint tar \\
                                    -v "$DEPLOY_MONGO_INIT_VOLUME:/init" nginx:alpine \\
                                    --no-same-owner -xf - -C /init
                        fi
                        echo "Deployment certificates and database initialization prepared."
                    '''
                }
            }
        }

        // ========================================
        // 9. Validate Docker Compose
        // ========================================
        stage('Validate Compose') {
            when {
                expression { env.BRANCH_NAME == 'main' && !env.CHANGE_ID && !currentBuild.getBuildCauses('hudson.triggers.TimerTrigger$TimerTriggerCause') }
            }
            steps {
                withCredentials([
                    file(
                        credentialsId: 'buy01-env',
                        variable: 'ENV_FILE'
                    )
                ]) {
                    sh '''
                        set +x
                        APP_IMAGE_TAG=${BUILD_NUMBER} \\
                        docker compose \\
                            -p "${DEPLOY_PROJECT:-buy01}" \\
                            --env-file "$ENV_FILE" \\
                            config > /dev/null
                        node jenkins-lab/check-deploy-env.mjs "$ENV_FILE"
                        echo "Docker Compose configuration is valid."
                    '''
                }
            }
        }

        // ========================================
        // 10. Automatic Deployment
        // ========================================
        stage('Deploy') {
            when {
                expression { env.BRANCH_NAME == 'main' && !env.CHANGE_ID && !currentBuild.getBuildCauses('hudson.triggers.TimerTrigger$TimerTriggerCause') }
            }
            steps {
                withCredentials([
                    file(
                        credentialsId: 'buy01-env',
                        variable: 'ENV_FILE'
                    )
                ]) {
                    script {
                        catchError(buildResult: 'FAILURE', stageResult: 'FAILURE', catchInterruptions: false) {
                            def status = sh(returnStatus: true, script: '''
                                set +x
                                echo "Deploying release #${BUILD_NUMBER}"
                                APP_IMAGE_TAG="$BUILD_NUMBER" docker compose -p "${DEPLOY_PROJECT:-buy01}" \\
                                    --env-file "$ENV_FILE" up -d --pull never
                            ''')
                            env.DEPLOY_EXIT_STATUS = status.toString()
                            if (status != 0) {
                                error("Compose failed to deploy release #${env.BUILD_NUMBER} (exit ${status})")
                            }
                        }
                    }
                }
            }
        }

        // ========================================
        // 11. Health Check + Automatic Rollback
        // ========================================
        stage('Post-Deployment Health Check') {
            when {
                expression { env.BRANCH_NAME == 'main' && !env.CHANGE_ID && !currentBuild.getBuildCauses('hudson.triggers.TimerTrigger$TimerTriggerCause') }
            }
            steps {
                withCredentials([
                    file(credentialsId: 'buy01-env', variable: 'ENV_FILE'),
                    string(credentialsId: 'nexus-docker-registry', variable: 'NEXUS_DOCKER_REGISTRY'),
                    usernamePassword(credentialsId: 'nexus-docker-reader', usernameVariable: 'NEXUS_DOCKER_READ_USERNAME', passwordVariable: 'NEXUS_DOCKER_READ_PASSWORD')
                ]) {
                    sh '''
                        set +x
                        set -eu
                        project="${DEPLOY_PROJECT:-buy01}"
                        state="/var/jenkins_home/deploy-secrets/$project"
                        release_file="$state/last-successful-release"

                        verify_release() {
                            release="$1"
                            manifest="$2"
                            shift 2
                            python3 scripts/nexus/images.py verify-deployment --release "$release" \\
                                --manifest "$manifest" --project "$project" --env-file "$ENV_FILE" "$@"
                        }

                        if [ "${DEPLOY_EXIT_STATUS:-1}" = 0 ] && verify_release "$BUILD_NUMBER" \\
                            "reports/nexus/release-$BUILD_NUMBER.json" --record-in "$state"; then
                            echo "RELEASE HEALTHY: #$BUILD_NUMBER"
                            exit 0
                        fi

                        echo "RELEASE FAILED: #$BUILD_NUMBER"
                        if [ ! -r "$release_file" ]; then
                            echo "ROLLBACK FAILED: last successful release pointer is unavailable: $release_file"
                            exit 1
                        fi
                        previous=$(cat "$release_file")
                        case "$previous" in
                            ''|0*|*[!0-9]*)
                                echo "ROLLBACK FAILED: invalid last successful release pointer: $release_file"
                                exit 1
                                ;;
                        esac
                        previous_manifest="$state/releases/release-$previous.json"
                        echo "Attempting rollback from #$BUILD_NUMBER to #$previous"
                        if ! python3 scripts/nexus/images.py pull --release "$previous" --manifest "$previous_manifest"; then
                            echo "ROLLBACK FAILED: could not restore images for #$previous after failed release #$BUILD_NUMBER"
                            exit 1
                        fi
                        if ! APP_IMAGE_TAG="$previous" docker compose -p "$project" \\
                            --env-file "$ENV_FILE" up -d --pull never; then
                            echo "ROLLBACK FAILED: Compose could not restore #$previous after failed release #$BUILD_NUMBER"
                            exit 1
                        fi
                        if verify_release "$previous" "$previous_manifest"; then
                            echo "ROLLBACK SUCCESSFUL: failed release #$BUILD_NUMBER, recovered release #$previous"
                        else
                            echo "ROLLBACK FAILED: #$previous failed health or image verification after failed release #$BUILD_NUMBER"
                        fi
                        exit 1
                    '''
                }
            }
        }
    }

    // ========================================
    // Final Pipeline Actions
    // ========================================
    post {
        success {
            echo """
            ==========================================
            PIPELINE SUCCESS
            Release #${BUILD_NUMBER}
            completed successfully. See the deployment
            and health-check stages for release status.
            Images:
            product-service:${BUILD_NUMBER}
            user-service:${BUILD_NUMBER}
            media-service:${BUILD_NUMBER}
            order-service:${BUILD_NUMBER}
            gateway:${BUILD_NUMBER}
            discovery:${BUILD_NUMBER}
            frontend:${BUILD_NUMBER}
            ==========================================
            """
            script {
                if (env.CI_NOTIFY_EMAIL?.trim()) {
                    try {
                        mail to: env.CI_NOTIFY_EMAIL,
                         subject: "SUCCESS: Build #${BUILD_NUMBER}",
                         body: """
                         Hello Team,
                         Build #${BUILD_NUMBER} completed successfully.
                         Check the deployment stage for release health results.
                         Regards,
                         Jenkins CI/CD
                         """
                    } catch (Exception e) {
                        echo "Email notification could not be delivered; check SMTP configuration."
                    }
                }
            }
        }
        failure {
            echo """
            ==========================================
            PIPELINE FAILED
            Build #${BUILD_NUMBER}
            The release failed.
            If a previous successful release existed,
            the pipeline attempted an automatic rollback.
            Check the Jenkins logs for details.
            ==========================================
            """
            script {
                if (env.CI_NOTIFY_EMAIL?.trim()) {
                    try {
                        mail to: env.CI_NOTIFY_EMAIL,
                         subject: "❌ FAILURE: Build #${BUILD_NUMBER}",
                         body: """
                         Attention Team,
                         Build #${BUILD_NUMBER} has FAILED.
                         Rollback may have been attempted if post-deploy health checks failed.
                         Regards,
                         Jenkins CI/CD
                         """
                    } catch (Exception e) {
                        echo "Email notification could not be delivered; check SMTP configuration."
                    }
                }
            }
        }
        always {
            script {
                if (env.WORKSPACE) {
                    archiveArtifacts artifacts: '**/target/site/jacoco/**, frontend/coverage/frontend/**', allowEmptyArchive: true
                    archiveArtifacts artifacts: 'reports/nexus/*.json', allowEmptyArchive: true
                    junit testResults: '**/target/surefire-reports/*.xml', allowEmptyResults: true
                } else {
                    echo 'Skipping report publication because the build workspace is unavailable.'
                }
            }
            echo 'Pipeline finished.'
        }
    }
}
