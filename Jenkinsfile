pipeline {
    agent any
    
    environment {
        // Kubernetes 설정
        K3S_NAMESPACE_DEV = 'dev'  // 개발 서버 네임스페이스
        K3S_NAMESPACE_PROD = 'default'  // 프로덕션 네임스페이스
        K3S_CONTEXT = 'default'
        
        // 이미지 설정
        IMAGE_NAME = 'recommend-service'
        IMAGE_REGISTRY = 'helena73'
        IMAGE_TAG = "${BUILD_NUMBER}"
        
        // 배포 서버 설정
        DEPLOY_SERVER = '3.35.66.197'
        DEPLOY_USER = 'ubuntu'
        DEPLOY_PATH = '/home/ubuntu/k3s-manifests'
        
        // SonarCloud 설정 (SonarQube 대신 SonarCloud 사용)
        SONAR_TOKEN_CREDENTIAL_ID = 'sonarcloud-token'  // SonarCloud 토큰
        SONAR_ORGANIZATION = 'devops-healthyreal'  // SonarCloud 조직명
        SONAR_PROJECT_KEY = 'devops-healthyreal_recommend-service'  // SonarCloud 프로젝트 키
        
        // 프로젝트 설정
        PROJECT_NAME = 'recommend-service'
        SERVICE_PORT = '5000'
        
        // Git 설정
        GIT_BRANCH = "${env.BRANCH_NAME ?: 'develop'}"
    }
    
    // develop 브랜치 push 시 자동 트리거
    triggers {
        githubPush()
    }
    
    stages {
        stage('Checkout') {
            steps {
                script {
                    // develop 브랜치만 체크아웃
                    checkout([$class: 'GitSCM', 
                        branches: [[name: "*/develop"]], 
                        userRemoteConfigs: scm.userRemoteConfigs
                    ])
                    
                    sh '''
                        echo "Checking out develop branch"
                        echo "Current commit: $(git rev-parse --short HEAD)"
                        echo "Branch: $(git rev-parse --abbrev-ref HEAD)"
                        echo "Commit message: $(git log -1 --pretty=%B)"
                    '''
                }
            }
        }
        
        stage('Build Docker Image') {
            steps {
                script {
                    sh '''
                        echo "Building Docker image"
                        docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} .
                        docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${IMAGE_NAME}:latest
                        docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${IMAGE_REGISTRY}/${IMAGE_NAME}:${BUILD_NUMBER}
                        docker tag ${IMAGE_NAME}:${BUILD_NUMBER} ${IMAGE_REGISTRY}/${IMAGE_NAME}:latest
                    '''
                }
            }
        }
        
        stage('Push Docker Image') {
            steps {
                script {
                    withCredentials([usernamePassword(credentialsId: 'dockerhub-credentials', 
                                                    usernameVariable: 'DOCKER_USER', 
                                                    passwordVariable: 'DOCKER_PASS')]) {
                        sh '''
                            echo "Pushing Docker image to registry"
                            echo ${DOCKER_PASS} | docker login -u ${DOCKER_USER} --password-stdin
                            docker push ${IMAGE_REGISTRY}/${IMAGE_NAME}:${BUILD_NUMBER}
                            docker push ${IMAGE_REGISTRY}/${IMAGE_NAME}:latest
                        '''
                    }
                }
            }
        }
        
        // develop 브랜치에서 Quality Gate 통과 시 개발 서버에 배포
        stage('Deploy to Dev Server') {
            when {
                branch 'develop'
            }
            steps {
                script {
                    sshagent(credentials: ['admin']) {
                        sh """
                            echo "Deploying to DEV server"
                            
                            ssh -o StrictHostKeyChecking=no ${DEPLOY_USER}@${DEPLOY_SERVER} << EOF
                                set -e
                                
                                # k3s kubectl 사용
                                export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
                                kubectl config use-context ${K3S_CONTEXT}
                                
                                # dev 네임스페이스가 없으면 생성
                                kubectl create namespace ${K3S_NAMESPACE_DEV} --dry-run=client -o yaml | kubectl apply -f -
                                
                                # 배포 디렉토리로 이동
                                cd ${DEPLOY_PATH}/${PROJECT_NAME}
                                
                                # Git에서 최신 코드 가져오기
                                git fetch origin
                                git checkout develop
                                git pull origin develop
                                
                                # 이미지 태그 업데이트 (app과 exporter 컨테이너 모두)
                                sed -i 's|image: ${IMAGE_REGISTRY}/${IMAGE_NAME}:.*|image: ${IMAGE_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}|g' k3s/deployment.yml
                                
                                # Kubernetes 리소스 배포 (dev 네임스페이스)
                                # promtail-config.yml (ConfigMap) 먼저 배포
                                if [ -f k3s/promtail-config.yml ]; then
                                    kubectl apply -f k3s/promtail-config.yml -n ${K3S_NAMESPACE_DEV}
                                fi
                                
                                # deployment.yml (Deployment, Service, ConfigMap 포함) 배포
                                kubectl apply -f k3s/deployment.yml -n ${K3S_NAMESPACE_DEV}
                                
                                # 배포 상태 확인
                                echo "Waiting for deployment rollout..."
                                kubectl rollout status deployment/${PROJECT_NAME} -n ${K3S_NAMESPACE_DEV} --timeout=300s
                                
                                # Pod 상태 확인
                                echo "========================================"
                                echo "Pod Status:"
                                kubectl get pods -l app=${PROJECT_NAME} -n ${K3S_NAMESPACE_DEV}
                                
                                echo "========================================"
                                echo "Service Status:"
                                kubectl get svc ${PROJECT_NAME} -n ${K3S_NAMESPACE_DEV}
                                
                                echo "========================================"
                                echo "Deployment Status:"
                                kubectl get deployment ${PROJECT_NAME} -n ${K3S_NAMESPACE_DEV}
                                
                                echo "Deployment to DEV server completed successfully"
                            EOF
                        """
                    }
                }
            }
        }
        
        // main 브랜치에서만 프로덕션 배포 (기존 로직 유지)
        stage('Deploy to Production') {
            when {
                branch 'main'
            }
            steps {
                script {
                    sshagent(credentials: ['admin']) {
                        sh """
                            echo "Deploying to PRODUCTION server"
                            
                            ssh -o StrictHostKeyChecking=no ${DEPLOY_USER}@${DEPLOY_SERVER} << EOF
                                set -e
                                
                                # k3s kubectl 사용
                                export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
                                kubectl config use-context ${K3S_CONTEXT}
                                
                                # 배포 디렉토리로 이동
                                cd ${DEPLOY_PATH}/${PROJECT_NAME}
                                
                                # Git에서 최신 코드 가져오기
                                git fetch origin
                                git checkout main
                                git pull origin main
                                
                                # 이미지 태그 업데이트
                                sed -i 's|image: ${IMAGE_REGISTRY}/${IMAGE_NAME}:.*|image: ${IMAGE_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}|g' k3s/deployment.yml
                                
                                # Kubernetes 리소스 배포 (프로덕션 네임스페이스)
                                if [ -f k3s/promtail-config.yml ]; then
                                    kubectl apply -f k3s/promtail-config.yml -n ${K3S_NAMESPACE_PROD}
                                fi
                                
                                kubectl apply -f k3s/deployment.yml -n ${K3S_NAMESPACE_PROD}
                                
                                # 배포 상태 확인
                                kubectl rollout status deployment/${PROJECT_NAME} -n ${K3S_NAMESPACE_PROD} --timeout=300s
                                
                                echo "Deployment to PRODUCTION completed successfully"
                            EOF
                        """
                    }
                }
            }
        }
    }
    
    post {
        success {
            echo "Pipeline completed successfully for build #${BUILD_NUMBER}"
        }
        failure {
            echo "Pipeline failed. Check logs for details."
        }
        always {
            sh 'docker system prune -f || true'
        }
    }
}