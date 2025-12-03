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

        // 배포 서버 설정 (팀 마스터 노드)
        DEPLOY_SERVER = '13.124.109.82'
        DEPLOY_USER = 'ubuntu'
        DEPLOY_PATH = '/home/ubuntu/k3s-manifests'

        // SonarCloud 설정
        SONAR_TOKEN_CREDENTIAL_ID = 'sonarcloud-token'
        SONAR_ORGANIZATION = 'devops-healthyreal'
        SONAR_PROJECT_KEY = 'devops-healthyreal_recommend-service'

        // GitHub 설정 (자동 Merge용)
        GITHUB_TOKEN_CREDENTIAL_ID = 'github-token'
    }

    triggers {
        githubPush()
    }

    stages {
        // 1. 코드 가져오기 & 브랜치 이름 파악
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

        // 2. [Develop 브랜치] SonarCloud 분석
        stage('SonarCloud Analysis') {
            when { branch 'develop' }
            steps {
                withSonarQubeEnv('SonarCloud') {
                    withCredentials([string(credentialsId: SONAR_TOKEN_CREDENTIAL_ID, variable: 'SONAR_TOKEN')]) {
                        sh '''
                            echo "Running SonarCloud analysis using Docker..."
                            
                            # 기존에 실패해서 남은 폴더 정리
                            rm -rf .scannerwork
                            
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

        // 3. [Develop 브랜치] Quality Gate 통과 대기
        stage('Quality Gate') {
            when { branch 'develop' }
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    // 분석 결과(Pass/Fail)를 기다림. 실패시 파이프라인 중단.
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        // 4. [Develop 브랜치] 통과 시 Main으로 자동 Merge & Push
        stage('Auto Merge to Main') {
            when { branch 'develop' }
            steps {
                withCredentials([usernamePassword(credentialsId: GITHUB_TOKEN_CREDENTIAL_ID, usernameVariable: 'GIT_USER', passwordVariable: 'GIT_TOKEN')]) {
                    sh '''
                        echo "Quality Gate Passed! Merging develop into main..."

                        # Git 설정 (Merge를 위해 필요)
                        git config user.email "jenkins@custom.com"
                        git config user.name "Jenkins Bot"

                        # 원격 브랜치 최신화
                        git fetch origin main

                        # main 브랜치로 이동 및 병합
                        git checkout main
                        git pull origin main
                        git merge origin/develop

                        # 인증 정보 포함해서 Push (https://토큰@주소 형식)
                        # 주의: GitHub URL에 토큰을 넣어 권한 문제를 해결함
                        git push https://${GIT_USER}:${GIT_TOKEN}@github.com/devops-healthyreal/recommend-service.git main
                    '''
                }
            }
        }

        /* 여기서 main으로 push가 일어나면, 젠킨스가 (Webhook 설정을 했다면)
           자동으로 다시 실행되면서 아래 'main' 브랜치용 Stage들이 실행됩니다.
        */

        // 5. [Main 브랜치] Docker Build & Push
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

        // 6. [Main 브랜치] 배포 (Production)
        stage('Deploy to Production') {
            when { branch 'main' }
            steps {
                sshagent(credentials: ['admin']) {
                    sh """
                        echo "Deploying to PRODUCTION server..."
                        ssh -o StrictHostKeyChecking=no ${DEPLOY_USER}@${DEPLOY_SERVER} << EOF
                            set -e
                            export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
                            
                            cd ${DEPLOY_PATH}/${IMAGE_NAME} || mkdir -p ${DEPLOY_PATH}/${IMAGE_NAME} && cd ${DEPLOY_PATH}/${IMAGE_NAME}
                            
                            # 최신 코드 받기 (deployment.yml 갱신용)
                            git fetch origin
                            git checkout main
                            git pull origin main
                            
                            # 이미지 태그 교체
                            sed -i 's|image: ${IMAGE_REGISTRY}/${IMAGE_NAME}:.*|image: ${IMAGE_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}|g' k3s/deployment.yml
                            
                            # 배포
                            kubectl apply -f k3s/deployment.yml -n ${K3S_NAMESPACE_PROD}
                            kubectl rollout status deployment/${IMAGE_NAME} -n ${K3S_NAMESPACE_PROD} --timeout=300s
                        EOF
                    """
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