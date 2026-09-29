pipeline {
    agent any

    options {
        // Prevent two Jenkins builds from deploying at the same time
        disableConcurrentBuilds()
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
                    sh './mvnw test'
                }
            }
        }

        stage('User Service Tests') {
            steps {
                dir('user-service') {
                    sh './mvnw test'
                }
            }
        }

        stage('Media Service Tests') {
            steps {
                dir('media-service') {
                    sh './mvnw test'
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

                            ./mvnw test
                        '''
                    }
                }
            }
        }

        stage('Discovery Tests') {
            steps {
                dir('discovery') {
                    sh './mvnw test'
                }
            }
        }


        // ========================================
        // 3. Package Backend
        // ========================================

        stage('Package Backend') {
            steps {

                dir('product-service') {
                    sh './mvnw package -DskipTests'
                }

                dir('user-service') {
                    sh './mvnw package -DskipTests'
                }

                dir('media-service') {
                    sh './mvnw package -DskipTests'
                }

                dir('gateway') {
                    sh './mvnw package -DskipTests'
                }

                dir('discovery') {
                    sh './mvnw package -DskipTests'
                }
            }
        }


        // ========================================
        // 4. Check Backend Artifacts
        // ========================================

        stage('Check Backend Artifacts') {
            steps {
                sh '''
                    echo "=== Product Service ==="
                    ls -lh product-service/target/*.jar

                    echo "=== User Service ==="
                    ls -lh user-service/target/*.jar

                    echo "=== Media Service ==="
                    ls -lh media-service/target/*.jar

                    echo "=== Gateway ==="
                    ls -lh gateway/target/*.jar

                    echo "=== Discovery ==="
                    ls -lh discovery/target/*.jar
                '''
            }
        }


        // ========================================
        // 5. Frontend CI
        // ========================================

        stage('Frontend CI') {
            steps {
                dir('frontend') {

                    // Install exact dependencies from package-lock.json
                    sh 'npm ci'

                    // Run tests once
                    sh 'CI=true npm test -- --no-watch --no-progress'

                    // Production build
                    sh 'npm run build'

                    // Check Angular build artifact
                    sh 'ls -la dist/frontend/browser'
                }
            }
        }


        // ========================================
        // 6. Build Docker Images
        // ========================================

        stage('Build Product Image') {
            steps {
                dir('product-service') {
                    sh '''
                        docker build \
                            -t product-service:${BUILD_NUMBER} \
                            .
                    '''
                }
            }
        }

        stage('Build User Image') {
            steps {
                dir('user-service') {
                    sh '''
                        docker build \
                            -t user-service:${BUILD_NUMBER} \
                            .
                    '''
                }
            }
        }

        stage('Build Media Image') {
            steps {
                dir('media-service') {
                    sh '''
                        docker build \
                            -t media-service:${BUILD_NUMBER} \
                            .
                    '''
                }
            }
        }

        stage('Build Gateway Image') {
            steps {
                dir('gateway') {
                    sh '''
                        docker build \
                            -t gateway:${BUILD_NUMBER} \
                            .
                    '''
                }
            }
        }

        stage('Build Discovery Image') {
            steps {
                dir('discovery') {
                    sh '''
                        docker build \
                            -t discovery:${BUILD_NUMBER} \
                            .
                    '''
                }
            }
        }

        stage('Build Frontend Image') {
            steps {
                dir('frontend') {
                    sh '''
                        docker build \
                            -t frontend:${BUILD_NUMBER} \
                            .
                    '''
                }
            }
        }


        // ========================================
        // 7. Check Complete Docker Release
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
                    docker image inspect gateway:${BUILD_NUMBER} > /dev/null
                    docker image inspect discovery:${BUILD_NUMBER} > /dev/null
                    docker image inspect frontend:${BUILD_NUMBER} > /dev/null

                    echo "All Docker images exist:"
                    echo "product-service:${BUILD_NUMBER}"
                    echo "user-service:${BUILD_NUMBER}"
                    echo "media-service:${BUILD_NUMBER}"
                    echo "gateway:${BUILD_NUMBER}"
                    echo "discovery:${BUILD_NUMBER}"
                    echo "frontend:${BUILD_NUMBER}"
                '''
            }
        }


        // ========================================
        // 8. Prepare TLS Certificates
        // ========================================

        stage('Prepare TLS Certificates') {
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

                        CERT_DIR="/var/jenkins_home/deploy-secrets/buy01/certs"

                        mkdir -p "$CERT_DIR"

                        cp "$P12_FILE" \
                           "$CERT_DIR/gateway-keystore.p12"

                        cp "$CRT_FILE" \
                           "$CERT_DIR/gateway-keystore.crt"

                        cp "$KEY_FILE" \
                           "$CERT_DIR/gateway-keystore.key"

                        chmod 600 \
                            "$CERT_DIR/gateway-keystore.p12"

                        chmod 644 \
                            "$CERT_DIR/gateway-keystore.crt"

                        chmod 600 \
                            "$CERT_DIR/gateway-keystore.key"

                        echo "TLS certificates prepared."
                    '''
                }
            }
        }


        // ========================================
        // 9. Validate Docker Compose
        // ========================================

        stage('Validate Compose') {
            steps {
                withCredentials([
                    file(
                        credentialsId: 'buy01-env',
                        variable: 'ENV_FILE'
                    )
                ]) {
                    sh '''
                        set +x

                        APP_IMAGE_TAG=${BUILD_NUMBER} \
                        docker compose \
                            -p buy01 \
                            --env-file "$ENV_FILE" \
                            config > /dev/null

                        echo "Docker Compose configuration is valid."
                    '''
                }
            }
        }


        // ========================================
        // 10. Automatic Deployment
        // ========================================

        stage('Deploy') {
            steps {
                withCredentials([
                    file(
                        credentialsId: 'buy01-env',
                        variable: 'ENV_FILE'
                    )
                ]) {
                    sh '''
                        set +x

                        echo "================================"
                        echo "Deploying release #${BUILD_NUMBER}"
                        echo "================================"

                        APP_IMAGE_TAG=${BUILD_NUMBER} \
                        docker compose \
                            -p buy01 \
                            --env-file "$ENV_FILE" \
                            up -d

                        echo "Release #${BUILD_NUMBER} containers started."
                    '''
                }
            }
        }


        // ========================================
        // 11. Post-Deployment Health Check
        // ========================================

        stage('Post-Deployment Health Check') {
            steps {
                sh '''
                    set +x

                    MAX_ATTEMPTS=18
                    SLEEP_SECONDS=5

                    check_container() {

                        CONTAINER="$1"

                        echo ""
                        echo "--------------------------------"
                        echo "Checking $CONTAINER"
                        echo "--------------------------------"

                        for i in $(seq 1 $MAX_ATTEMPTS); do

                            STATE=$(docker inspect \
                                --format='{{.State.Status}}' \
                                "$CONTAINER" \
                                2>/dev/null || echo "missing")

                            HEALTH=$(docker inspect \
                                --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' \
                                "$CONTAINER" \
                                2>/dev/null || echo "missing")

                            echo "Attempt $i/$MAX_ATTEMPTS -> state=$STATE health=$HEALTH"

                            # Container disappeared or crashed
                            if [ "$STATE" = "exited" ] || \
                               [ "$STATE" = "dead" ] || \
                               [ "$STATE" = "missing" ]; then

                                echo "ERROR: $CONTAINER stopped unexpectedly."

                                return 1
                            fi


                            # Real Docker healthcheck succeeded
                            if [ "$HEALTH" = "healthy" ]; then

                                echo "$CONTAINER is healthy."

                                return 0
                            fi


                            # Temporary fallback:
                            # service has no Docker HEALTHCHECK yet,
                            # but its main process is still running.
                            if [ "$HEALTH" = "no-healthcheck" ] && \
                               [ "$STATE" = "running" ]; then

                                echo "$CONTAINER is running."
                                echo "WARNING: no Docker healthcheck configured."

                                return 0
                            fi


                            sleep $SLEEP_SECONDS
                        done


                        echo "ERROR: $CONTAINER did not become healthy within the timeout."

                        return 1
                    }


                    # ==================================
                    # Databases
                    # ==================================

                    check_container product-mongodb
                    check_container media-mongodb
                    check_container user-mongodb


                    # ==================================
                    # Infrastructure
                    # ==================================

                    check_container buy01-kafka
                    check_container buy01-discovery


                    # ==================================
                    # Backend Services
                    # ==================================

                    check_container buy01-user-service
                    check_container buy01-product-service
                    check_container buy01-media-service
                    check_container buy01-gateway


                    # ==================================
                    # Frontend
                    # ==================================

                    check_container buy01-frontend


                    echo ""
                    echo "================================"
                    echo "Release #${BUILD_NUMBER}"
                    echo "passed deployment checks."
                    echo "================================"
                '''
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
            successfully built and deployed.

            Images:

            product-service:${BUILD_NUMBER}
            user-service:${BUILD_NUMBER}
            media-service:${BUILD_NUMBER}
            gateway:${BUILD_NUMBER}
            discovery:${BUILD_NUMBER}
            frontend:${BUILD_NUMBER}

            ==========================================
            """
        }


        failure {
            echo """
            ==========================================
            PIPELINE FAILED

            Build #${BUILD_NUMBER}

            Check the failed Jenkins stage
            and its logs for details.

            ==========================================
            """
        }


        always {
            echo "Pipeline finished."
        }
    }
}