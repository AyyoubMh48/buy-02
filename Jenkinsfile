pipeline {
    agent any

    stages {

        stage('Docker Check') {
            steps {
                sh 'docker version'
            }
        }

        // =========================
        // Backend Tests
        // =========================

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
                dir('gateway') {
                    sh './mvnw test'
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

        // =========================
        // Backend Package
        // =========================

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

        // =========================
        // Check Artifacts
        // =========================

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

        // =========================
        // Product Docker Image
        // =========================

        stage('Build Product Docker Image') {
            steps {
                dir('product-service') {
                    sh 'docker build -t product-service:${BUILD_NUMBER} .'
                }
            }
        }

        stage('Check Docker Image') {
            steps {
                sh 'docker image ls product-service'
            }
        }
    }

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