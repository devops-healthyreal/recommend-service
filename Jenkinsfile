pipeline {
    agent any

    environment {
        // Kubernetes
        K3S_NAMESPACE_DEV = 'dev'
        K3S_NAMESPACE_PROD = 'default'
        K3S_CONTEXT = 'default'

        // Image
        IMAGE_NAME = 'recommend-service'
        IMAGE_REGISTRY = 'helena73'
        IMAGE_TAG = "${BUILD_NUMBER}"

        // Deploy server
        DEPLOY_SERVER = '13.124.109.82'
        DEPLOY_USER = 'ubuntu'
        DEPLOY_PATH = '/home/ubuntu/k3s-manifests'

        // SonarCloud
        SONAR_TOKEN_CREDENTIAL_ID = 'sonarcloud-token'
        SONAR_ORGANIZATION = 'devops-healthyreal'
        SONAR_PROJECT_KEY = 'devops-healthyreal_recommend-service'

        // GitHub Token for auto PR
        GITHUB_TOKEN_CREDENTIAL_ID = 'github-token'
        REPO = "devops-healthyreal/recommend-service"
    }

    triggers {
        githubPush()
    }

    stages {

        stage('Checkout') {
            steps {
                checkout(scm)
            }
        }

        stage('Detect Branch Name') {
            steps {
                script {
                    // 1. Jenkins가 제공하는 GIT_BRANCH 변수 확인 (예: origin/develop)
                    def rawBranch = env.GIT_BRANCH
                    
                    if (rawBranch) {
                        // 2. 'origin/' 같은 접두사 제거하고 순수 브랜치 이름만 추출
                        // 예: origin/develop -> develop
                        // 예: origin/main -> main
                        env.BRANCH_NAME = rawBranch.split('/').last()
                    } else {
                        // 3. 만약 변수가 없으면 git 명령어로 시도 (혹시 모를 대비)
                        env.BRANCH_NAME = sh(returnStdout: true, script: 'git rev-parse --abbrev-ref HEAD').trim()
                    }

                    echo ">>> Detected Branch Raw: ${rawBranch}"
                    echo ">>> Final Branch Name: ${env.BRANCH_NAME}"
                }
            }
        }

        /* ----------------------------------------
           1) DEVELOP BRANCH → SONARCLOUD 분석
        ---------------------------------------- */
        stage('SonarCloud Analysis') {
            when { branch 'develop' }
            steps {
                script { // script 블록으로 감싸주세요
                    withCredentials([string(credentialsId: SONAR_TOKEN_CREDENTIAL_ID, variable: 'SONAR_TOKEN')]) {
                        sh '''
                            echo "Running SonarCloud analysis using Docker..."
                            
                            # docker run 명령어로 스캐너 실행 (unzip 불필요)
                            # $(pwd):/usr/src -> 현재 젠킨스 작업 폴더를 컨테이너에 연결
                            docker run --rm \
                                -e SONAR_TOKEN="${SONAR_TOKEN}" \
                                -e SONAR_HOST_URL="https://sonarcloud.io" \
                                -v "$(pwd):/usr/src" \
                                sonarsource/sonar-scanner-cli \
                                -Dsonar.organization=${SONAR_ORGANIZATION} \
                                -Dsonar.projectKey=${SONAR_PROJECT_KEY} \
                                -Dsonar.sources=. \
                                -Dsonar.sourceEncoding=UTF-8 \
                                -Dsonar.python.version=3.11
                        '''
                    }
                }
            }
        }

        /* ----------------------------------------
           2) SONARCLOUD QUALITY GATE 확인
        ---------------------------------------- */
        stage('Quality Gate') {
            when { branch 'develop' }
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        /* ----------------------------------------
           3) QUALITY GATE SUCCESS → MAIN 자동 PR 생성
        ---------------------------------------- */
        stage('Create PR to main') {
            when { branch 'develop' }
            steps {
                withCredentials([string(credentialsId: GITHUB_TOKEN_CREDENTIAL_ID, variable: 'GITHUB_TOKEN')]) {
                    sh '''
                        echo "Creating PR from develop to main..."

                        curl -X POST \
                          -H "Authorization: token $GITHUB_TOKEN" \
                          -H "Accept: application/vnd.github+json" \
                          https://api.github.com/repos/${REPO}/pulls \
                          -d '{
                            "title": "Auto PR: develop → main (SonarCloud Passed)",
                            "head": "develop",
                            "base": "main",
                            "body": "This PR was automatically created after SonarCloud quality gate passed."
                          }'
                    '''
                }
            }
        }

        /* ----------------------------------------
           4) MAIN BRANCH → DOCKER BUILD + PUSH
        ---------------------------------------- */
        stage('Build Docker Image') {
            when { branch 'main' }
            steps {
                sh '''
                    echo "Building Docker image"
                    docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_REGISTRY}/${IMAGE_NAME}:latest
                '''
            }
        }

        stage('Push Docker Image') {
            when { branch 'main' }
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-credentials',
                                                  usernameVariable: 'DOCKER_USER',
                                                  passwordVariable: 'DOCKER_PASS')]) {
                    sh '''
                        echo "Pushing Docker image"
                        echo ${DOCKER_PASS} | docker login -u ${DOCKER_USER} --password-stdin
                        docker push ${IMAGE_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
                        docker push ${IMAGE_REGISTRY}/${IMAGE_NAME}:latest
                    '''
                }
            }
        }

        /* ----------------------------------------
           5) MAIN MERGE 이후 → DEPLOY
        ---------------------------------------- */
        stage('Deploy to Dev') {
            when { branch 'main' }
            steps {
                script {
                    sshagent(credentials: ['admin']) {
                        sh """
                        ssh -o StrictHostKeyChecking=no ${DEPLOY_USER}@${DEPLOY_SERVER} << EOF
                            set -e
                            export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

                            kubectl create namespace ${K3S_NAMESPACE_DEV} --dry-run=client -o yaml | kubectl apply -f -

                            cd ${DEPLOY_PATH}/${IMAGE_NAME}
                            git pull origin main

                            sed -i 's|image: .*|image: ${IMAGE_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}|g' k3s/deployment.yml

                            kubectl apply -f k3s/deployment.yml -n ${K3S_NAMESPACE_DEV}
                            kubectl rollout status deployment/${IMAGE_NAME} -n ${K3S_NAMESPACE_DEV} --timeout=300s
                        EOF
                        """
                    }
                }
            }
        }

        stage('Deploy to Production') {
            when { branch 'main' }
            steps {
                script {
                    sshagent(credentials: ['admin']) {
                        sh """
                        ssh -o StrictHostKeyChecking=no ${DEPLOY_USER}@${DEPLOY_SERVER} << EOF
                            set -e
                            export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

                            cd ${DEPLOY_PATH}/${IMAGE_NAME}
                            git pull origin main

                            sed -i 's|image: .*|image: ${IMAGE_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}|g' k3s/deployment.yml

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
        success { echo "Pipeline completed successfully!" }
        failure { echo "Pipeline failed." }
    }
}
