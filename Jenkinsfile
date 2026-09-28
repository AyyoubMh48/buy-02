pipeline {
    agent any

      stages {

        stage('Product Service Tests') {
            steps {
                dir('product-service') {
                    sh './mvnw test'
                }
            }
        }

        stage('Product Service Package') {
            steps {
                dir('product-service') {
                    sh './mvnw package -DskipTests'
                    sh 'ls -lh target/'
                }
            }
        }

        stage('Docker Check') {
            steps {
                sh 'docker version'
            }
        }

        stage('Product Service Docker Build') {
            steps {
                dir('product-service') {
                    sh 'docker build -t product-service:${BUILD_NUMBER} .'
                }
            }
        }

        stage('Docker Image Check') {
            steps {
                sh 'docker image ls product-service'
            }
        }
    }
}
    /* stage('Frontend Tests') {
            steps {
                dir('frontend') {
                    sh 'npm ci'
                    sh 'npm run test:ci'
                }
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'frontend/test-results.xml'
                }
            }
        }*/
