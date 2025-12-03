pipeline {
    agent any

    environment {
        // Kubernetes 설정
        K3S_NAMESPACE_DEV = 'dev'
        K3S_NAMESPACE_PROD = 'default'
        K3S_CONTEXT = 'default'

        // 이미지 설정
        IMAGE_NAME = 'recommend-service'
        IMAGE_REGISTRY = 'helena73'
        IMAGE_TAG = "${BUILD_NUMBER}"

        DEPLOY_SERVER = '13.124.109.82'
        DEPLOY_USER = 'ubuntu'
        DEPLOY_PATH = '/home/ubuntu/k3s-manifests'

        // SonarCloud 설정
        SONAR_TOKEN_CREDENTIAL_ID = 'sonarcloud-token'
        SONAR_ORGANIZATION = 'devops-healthyreal'
        SONAR_PROJECT_KEY = 'devops-healthyreal_recommend-service'

        // GitHub 설정 (자동 Merge용)
        GITHUB_TOKEN_CREDENTIAL_ID = 'github-token'
        REPO = 'devops-healthyreal/recommend-service'
    }

    triggers {
        githubPush()
    }

    stages {
        stage('Checkout & Detect Branch') {
            steps {
                checkout scm
                script {
                    def rawBranch = env.GIT_BRANCH
                    if (rawBranch) {
                        env.BRANCH_NAME = rawBranch.split('/').last()
                    } else {
                        env.BRANCH_NAME = sh(returnStdout: true, script: 'git rev-parse --abbrev-ref HEAD').trim()
                    }
                    echo ">>> Current Branch: ${env.BRANCH_NAME}"
                }
            }
        }

        stage('SonarCloud Analysis') {
            when { branch 'develop' }
            steps {
                withSonarQubeEnv('SonarCloud') {
                    withCredentials([string(credentialsId: SONAR_TOKEN_CREDENTIAL_ID, variable: 'SONAR_TOKEN')]) {
                        sh '''
                            echo "Running SonarCloud analysis using Docker..."
                            docker run --rm -u 0 -v "$(pwd):/usr/src" --entrypoint /bin/sh sonarsource/sonar-scanner-cli -c "rm -rf /usr/src/.scannerwork"
                            docker run --rm \
                                -u 0 \
                                -e SONAR_TOKEN="${SONAR_TOKEN}" \
                                -e SONAR_HOST_URL="https://sonarcloud.io" \
                                -v "$(pwd):/usr/src" \
                                sonarsource/sonar-scanner-cli \
                                -Dsonar.organization=${SONAR_ORGANIZATION} \
                                -Dsonar.projectKey=${SONAR_PROJECT_KEY} \
                                -Dsonar.sources=. \
                                -Dsonar.sourceEncoding=UTF-8 \
                                -Dsonar.python.version=3.11 \
                                -Dsonar.working.directory=/usr/src/.scannerwork
                        '''
                    }
                }
            }
        }

        stage('Quality Gate') {
            when { branch 'develop' }
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Create PR to Main') {
            when { branch 'develop' }
            steps {
                withCredentials([usernamePassword(credentialsId: GITHUB_TOKEN_CREDENTIAL_ID, usernameVariable: 'GIT_USER', passwordVariable: 'GITHUB_TOKEN')]) {
                    sh '''
                        echo "Quality Gate Passed! Creating PR from develop to main..."
                        
                        curl -L \
                          -X POST \
                          -H "Accept: application/vnd.github+json" \
                          -H "Authorization: Bearer $GITHUB_TOKEN" \
                          -H "X-GitHub-Api-Version: 2022-11-28" \
                          "https://api.github.com/repos/devops-healthyreal/recommend-service/pulls" \
                          -d '{
                                "title":"[Auto] develop -> main (SonarCloud Passed)",
                                "body":"SonarCloud Quality Gate를 통과했습니다. main 브랜치로 배포를 준비해주세요.",
                                "head":"develop",
                                "base":"main"
                              }'
                    '''
                }
            }
        }

        stage('Build Docker Image') {
            when { branch 'main' }
            steps {
                sh '''
                    echo "Building Docker image for Production"
                    docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_REGISTRY}/${IMAGE_NAME}:latest
                '''
                withCredentials([usernamePassword(credentialsId: 'dockerhub-credentials', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                    sh '''
                        echo ${DOCKER_PASS} | docker login -u ${DOCKER_USER} --password-stdin
                        docker push ${IMAGE_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
                        docker push ${IMAGE_REGISTRY}/${IMAGE_NAME}:latest
                    '''
                }
            }
        }     
        
        stage('Deploy to Production') {
            when { branch 'main' }
            steps {
                withCredentials([usernamePassword(credentialsId: GITHUB_TOKEN_CREDENTIAL_ID, usernameVariable: 'GIT_USER', passwordVariable: 'GITHUB_TOKEN')]) {
                    sshagent(credentials: ['admin']) {                         
                        sh """
                            echo "Deploying to PRODUCTION server..."
                            
                            ssh -o StrictHostKeyChecking=no ${DEPLOY_USER}@${DEPLOY_SERVER} << EOF
                                set -e
                                export KUBECONFIG=/etc/rancher/k3s/k3s.yaml                                
                        
                                echo "Removing existing directory for clean clone..."
                                rm -rf ${DEPLOY_PATH}/${IMAGE_NAME}
                                
                                echo "Cloning repository..."
                                git clone https://git:${GITHUB_TOKEN}@github.com/${REPO}.git ${DEPLOY_PATH}/${IMAGE_NAME}
                                
                                cd ${DEPLOY_PATH}/${IMAGE_NAME}
                                sed -i 's|image: ${IMAGE_REGISTRY}/${IMAGE_NAME}:.*|image: ${IMAGE_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}|g' k3s/deployment.yml
                                
                                kubectl apply -f k3s/deployment.yml -n ${K3S_NAMESPACE_PROD}
                                
                                kubectl rollout status deployment/${IMAGE_NAME} -n ${K3S_NAMESPACE_PROD} --timeout=300s
EOF
                        """
                    }
                }
            }
        }
    }

    post {
        always {
            sh 'docker system prune -f || true'
        }
        success {
            echo "Pipeline succeeded!"
        }
        failure {
            echo "Pipeline failed."
        }
    }
}