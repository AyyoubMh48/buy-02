pipeline {
    agent any

    stages {

        // ========================================
        // 1. Docker Environment
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
        // 5. Frontend
        // ========================================

        stage('Frontend CI') {
            steps {
                dir('frontend') {

                    sh 'npm ci'

                    sh 'CI=true npm test -- --no-watch --no-progress'

                    sh 'npm run build'

                    sh 'ls -la dist/frontend/browser'
                }
            }
        }


        // ========================================
        // 6. Docker Images
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
        // 8. Validate Docker Compose
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
                            --env-file "$ENV_FILE" \
                            config > /dev/null

                        echo "Docker Compose configuration is valid"
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
            BUILD SUCCESS
            Release: ${BUILD_NUMBER}

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
            Build: ${BUILD_NUMBER}

            Deployment was NOT performed.
            ==========================================
            """
        }

        always {
            echo "Pipeline finished."
        }
    }
}