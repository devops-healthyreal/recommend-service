pipeline {
    agent any
    
    environment {
        // Kubernetes 설정
        K3S_NAMESPACE = 'default'
        K3S_CONTEXT = 'default'
        
        // 이미지 설정
        IMAGE_NAME = 'recommend-service'
        IMAGE_REGISTRY = 'helena73'
        IMAGE_TAG = "${BUILD_NUMBER}"
        
        // 배포 서버 설정
        DEPLOY_SERVER = '3.35.66.197'
        DEPLOY_USER = 'ubuntu'
        DEPLOY_PATH = '/home/ubuntu/k3s-manifests'
        
        // SonarQube 설정
        SONAR_HOST_URL = 'http://3.35.66.197:9000'
        SONAR_TOKEN_CREDENTIAL_ID = 'sonar-token'
        
        // 프로젝트 설정
        PROJECT_NAME = 'recommend-service'
        SERVICE_PORT = '5000'
        
        // Git 설정
        GIT_BRANCH = "${env.BRANCH_NAME ?: 'develop'}"
    }
    
    stages {
        stage('Checkout') {
            steps {
                script {
                    // develop 브랜치 체크아웃
                    checkout([$class: 'GitSCM', 
                        branches: [[name: "*/develop"]], 
                        userRemoteConfigs: scm.userRemoteConfigs
                    ])
                    
                    sh '''
                        echo "========================================"
                        echo "Checking out develop branch..."
                        echo "========================================"
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
                        echo "========================================"
                        echo "Building Docker image..."
                        echo "========================================"
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
                            echo "========================================"
                            echo "Pushing Docker image to registry..."
                            echo "========================================"
                            echo ${DOCKER_PASS} | docker login -u ${DOCKER_USER} --password-stdin
                            docker push ${IMAGE_REGISTRY}/${IMAGE_NAME}:${BUILD_NUMBER}
                            docker push ${IMAGE_REGISTRY}/${IMAGE_NAME}:latest
                        '''
                    }
                }
            }
        }
        
        stage('SonarQube Analysis') {
            steps {
                script {
                    withCredentials([string(credentialsId: "${SONAR_TOKEN_CREDENTIAL_ID}", variable: 'SONAR_TOKEN_VAR')]) {
                        sh '''
                            echo "========================================"
                            echo "Running SonarQube analysis..."
                            echo "========================================"
                            
                            # SonarQube Scanner 설치 확인
                            if ! command -v sonar-scanner &> /dev/null; then
                                echo "Installing SonarQube Scanner..."
                                wget -q https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-5.0.1.3006-linux.zip
                                unzip -q sonar-scanner-cli-5.0.1.3006-linux.zip
                                export PATH=$PATH:$(pwd)/sonar-scanner-5.0.1.3006-linux/bin
                            fi
                            
                            # SonarQube 분석 실행
                            sonar-scanner \
                                -Dsonar.host.url=${SONAR_HOST_URL} \
                                -Dsonar.login=${SONAR_TOKEN_VAR} \
                                -Dsonar.projectKey=${PROJECT_NAME} \
                                -Dsonar.projectName=${PROJECT_NAME} \
                                -Dsonar.sources=. \
                                -Dsonar.sourceEncoding=UTF-8 \
                                -Dsonar.python.version=3.11
                        '''
                    }
                }
            }
        }
        
        stage('Quality Gate Check') {
            steps {
                script {
                    withCredentials([string(credentialsId: "${SONAR_TOKEN_CREDENTIAL_ID}", variable: 'SONAR_TOKEN_VAR')]) {
                        sh '''
                            echo "========================================"
                            echo "Checking SonarQube Quality Gate..."
                            echo "========================================"
                            
                            # 분석 완료 대기
                            sleep 15
                            
                            # Quality Gate 상태 확인
                            PROJECT_KEY="${PROJECT_NAME}"
                            MAX_RETRIES=10
                            RETRY_COUNT=0
                            
                            while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
                                QG_STATUS=$(curl -s -u ${SONAR_TOKEN_VAR}: "${SONAR_HOST_URL}/api/qualitygates/project_status?projectKey=${PROJECT_KEY}" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
                                
                                if [ -n "$QG_STATUS" ]; then
                                    echo "Quality Gate Status: ${QG_STATUS}"
                                    
                                    if [ "${QG_STATUS}" = "OK" ]; then
                                        echo "✅ Quality Gate PASSED!"
                                        exit 0
                                    elif [ "${QG_STATUS}" = "ERROR" ]; then
                                        echo "❌ Quality Gate FAILED!"
                                        exit 1
                                    fi
                                fi
                                
                                RETRY_COUNT=$((RETRY_COUNT + 1))
                                echo "Waiting for Quality Gate result... (${RETRY_COUNT}/${MAX_RETRIES})"
                                sleep 5
                            done
                            
                            echo "⚠️ Quality Gate check timeout"
                            exit 1
                        '''
                    }
                }
            }
        }
        
        stage('Merge to Main') {
            when {
                // Quality Gate 통과 후에만 실행
                expression { 
                    return true 
                }
            }
            steps {
                script {
                    sh '''
                        echo "========================================"
                        echo "Merging develop to main..."
                        echo "========================================"
                        
                        git config user.name "Jenkins"
                        git config user.email "jenkins@healthyreal.com"
                        
                        # main 브랜치로 체크아웃
                        git checkout main
                        git pull origin main
                        
                        # develop 브랜치 merge
                        git merge develop -m "Merge develop to main after SonarQube Quality Gate passed [Build #${BUILD_NUMBER}]"
                        
                        # main 브랜치에 푸시
                        git push origin main
                        
                        echo "✅ Merged to main successfully"
                    '''
                }
            }
        }
        
        stage('Deploy to k3s') {
            when {
                branch 'main'
            }
            steps {
                script {
                    sshagent(credentials: ['admin']) {
                        sh """
                            echo "========================================"
                            echo "Deploying to k3s cluster..."
                            echo "========================================"
                            
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
                                
                                # 이미지 태그 업데이트 (app과 exporter 컨테이너 모두)
                                sed -i 's|image: ${IMAGE_REGISTRY}/${IMAGE_NAME}:.*|image: ${IMAGE_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}|g' k3s/deployment.yml
                                
                                # Kubernetes 리소스 배포
                                # promtail-config.yml (ConfigMap) 먼저 배포
                                if [ -f k3s/promtail-config.yml ]; then
                                    kubectl apply -f k3s/promtail-config.yml -n ${K3S_NAMESPACE}
                                fi
                                
                                # deployment.yml (Deployment, Service, ConfigMap 포함) 배포
                                kubectl apply -f k3s/deployment.yml -n ${K3S_NAMESPACE}
                                
                                # 배포 상태 확인
                                echo "Waiting for deployment rollout..."
                                kubectl rollout status deployment/${PROJECT_NAME} -n ${K3S_NAMESPACE} --timeout=300s
                                
                                # Pod 상태 확인
                                echo "========================================"
                                echo "Pod Status:"
                                kubectl get pods -l app=${PROJECT_NAME} -n ${K3S_NAMESPACE}
                                
                                echo "========================================"
                                echo "Service Status:"
                                kubectl get svc ${PROJECT_NAME} -n ${K3S_NAMESPACE}
                                
                                echo "========================================"
                                echo "Deployment Status:"
                                kubectl get deployment ${PROJECT_NAME} -n ${K3S_NAMESPACE}
                                
                                echo "✅ Deployment completed successfully"
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