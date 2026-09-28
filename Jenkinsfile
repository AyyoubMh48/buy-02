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
                sh 'docker --version'
            }
        }
    }
}