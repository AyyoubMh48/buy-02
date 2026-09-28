pipeline {
    agent any

    stages {

  
        stage('Docker Check') {
            steps {
                sh 'docker version'
            }
        }



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



        stage('Build Product Docker Image') {
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


  
        stage('Build Frontend Docker Image') {
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




        stage('Check Docker Images') {
            steps {
                sh '''
                    echo "=== Product Service Images ==="
                    docker image ls product-service

                    echo "=== Frontend Images ==="
                    docker image ls frontend
                '''
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

                        PRODUCT_IMAGE_TAG=${BUILD_NUMBER} \
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
    // Final actions
    // ========================================

    post {

        success {
            echo "Pipeline SUCCESS - Build #${BUILD_NUMBER}"
        }

        failure {
            echo "Pipeline FAILED - Build #${BUILD_NUMBER}"
        }

        always {
            echo "Pipeline finished."
        }
    }
}