pipeline {
    agent any

    stages {
        stage('Check Product Service') {
            steps {
                dir('product-service') {
                    sh 'pwd'
                    sh 'ls -la'
                }
            }
        }
    }
}