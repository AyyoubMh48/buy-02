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

        stage('Frontend Tests') {
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
                sh 'docker --version'
            }
        }
    }
}