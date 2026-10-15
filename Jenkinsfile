pipeline {
    agent any

    environment {
        APP_NAME        = 'task-manager'
        DOCKERHUB_USER  = 'Mohan815'
        IMAGE_NAME      = "${DOCKERHUB_USER}/${APP_NAME}"
        IMAGE_TAG       = "${env.BUILD_NUMBER}"
        K8S_NAMESPACE   = 'task-manager'
        DOCKER_CREDS    = 'dockerhub-creds'
        KUBECONFIG_CRED = 'kubeconfig'
    }

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
        disableConcurrentBuilds()
    }

    triggers {
        pollSCM('H/2 * * * *')
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.GIT_SHORT = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                }
                echo "Building commit ${env.GIT_SHORT} as ${IMAGE_NAME}:${IMAGE_TAG}"
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip -q
                    pip install -r requirements-dev.txt -q
                '''
            }
        }

        stage('Lint') {
            steps {
                sh '. venv/bin/activate && flake8 app tests'
            }
        }

        stage('Unit Tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    pytest tests --junitxml=test-results.xml \
                                 --cov=app --cov-report=xml --cov-report=term \
                                 --cov-fail-under=80
                '''
            }
            post {
                always {
                    junit 'test-results.xml'
                    archiveArtifacts artifacts: 'coverage.xml', allowEmptyArchive: true
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                sh """
                    docker build \
                      --build-arg APP_VERSION=${GIT_SHORT} \
                      --build-arg BUILD_NUMBER=${IMAGE_TAG} \
                      -t ${IMAGE_NAME}:${IMAGE_TAG} \
                      -t ${IMAGE_NAME}:latest .
                """
            }
        }

        stage('Smoke Test Container') {
            steps {
                sh """
                    docker rm -f ${APP_NAME}-smoke 2>/dev/null || true
                    docker run -d --name ${APP_NAME}-smoke ${IMAGE_NAME}:${IMAGE_TAG}
                    sleep 5
                    docker exec ${APP_NAME}-smoke python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:5000/health').read().decode())"
                """
            }
            post {
                always {
                    sh "docker rm -f ${APP_NAME}-smoke || true"
                }
            }
        }

        stage('Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(credentialsId: "${DOCKER_CREDS}",
                                                  usernameVariable: 'DH_USER',
                                                  passwordVariable: 'DH_PASS')]) {
                    sh '''
                        echo "$DH_PASS" | docker login -u "$DH_USER" --password-stdin
                        docker push ${IMAGE_NAME}:${IMAGE_TAG}
                        docker push ${IMAGE_NAME}:latest
                        docker logout
                    '''
                }
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                script { env.DEPLOY_STARTED = 'true' }
                withCredentials([file(credentialsId: "${KUBECONFIG_CRED}", variable: 'KUBECONFIG')]) {
                    sh '''
                        kubectl apply -f k8s/namespace.yaml
                        kubectl apply -f k8s/configmap.yaml
                        kubectl apply -f k8s/service.yaml

                        sed "s|IMAGE_PLACEHOLDER|${IMAGE_NAME}:${IMAGE_TAG}|g" k8s/deployment.yaml | kubectl apply -f -

                        kubectl annotate deployment/${APP_NAME} -n ${K8S_NAMESPACE} \
                            kubernetes.io/change-cause="Jenkins build #${IMAGE_TAG} (commit ${GIT_SHORT})" --overwrite
                    '''
                }
            }
        }

        stage('Verify Rollout') {
            steps {
                withCredentials([file(credentialsId: "${KUBECONFIG_CRED}", variable: 'KUBECONFIG')]) {
                    sh '''
                        kubectl rollout status deployment/${APP_NAME} -n ${K8S_NAMESPACE} --timeout=180s
                        kubectl get pods,svc -n ${K8S_NAMESPACE} -o wide
                    '''
                }
            }
        }
    }

    post {
        success {
            echo "SUCCESS: ${IMAGE_NAME}:${IMAGE_TAG} is live on Kubernetes (NodePort 30080)"
        }
        failure {
            script {
                if (env.DEPLOY_STARTED == 'true') {
                    echo 'Deployment failed - rolling back to the previous Kubernetes revision'
                    withCredentials([file(credentialsId: "${KUBECONFIG_CRED}", variable: 'KUBECONFIG')]) {
                        sh 'kubectl rollout undo deployment/${APP_NAME} -n ${K8S_NAMESPACE} || true'
                    }
                } else {
                    echo 'Pipeline failed before deployment - nothing to roll back'
                }
            }
        }
        always {
            sh "docker rmi ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest || true"
            cleanWs()
        }
    }
}
