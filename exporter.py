#!/usr/bin/env python3
"""
Prometheus metrics exporter for recommend-service
"""
import os
import time
import psutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from prometheus_client import Counter, Gauge, Histogram, generate_latest, REGISTRY

# Metrics 정의
REQUEST_COUNT = Counter(
    'recommend_service_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'recommend_service_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint']
)

APP_INFO = Gauge(
    'recommend_service_info',
    'Application information',
    ['version', 'environment']
)

SYSTEM_CPU = Gauge(
    'recommend_service_cpu_usage_percent',
    'CPU usage percentage'
)

SYSTEM_MEMORY = Gauge(
    'recommend_service_memory_usage_bytes',
    'Memory usage in bytes'
)

SYSTEM_MEMORY_PERCENT = Gauge(
    'recommend_service_memory_usage_percent',
    'Memory usage percentage'
)

# 초기 메트릭 설정
APP_INFO.labels(version='1.0.0', environment=os.getenv('FLASK_ENV', 'production')).set(1)

class MetricsHandler(BaseHTTPRequestHandler):
    """Prometheus metrics endpoint handler"""
    
    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4')
            self.end_headers()
            self.wfile.write(generate_latest(REGISTRY))
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"healthy"}')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # 로그 출력 억제
        pass

def update_system_metrics():
    """시스템 메트릭 업데이트"""
    try:
        # CPU 사용률
        cpu_percent = psutil.cpu_percent(interval=1)
        SYSTEM_CPU.set(cpu_percent)
        
        # 메모리 사용량
        process = psutil.Process()
        memory_info = process.memory_info()
        SYSTEM_MEMORY.set(memory_info.rss)
        SYSTEM_MEMORY_PERCENT.set(process.memory_percent())
    except Exception as e:
        print(f"Error updating system metrics: {e}")

def run_exporter(port=9090):
    """Exporter 서버 실행"""
    server = HTTPServer(('0.0.0.0', port), MetricsHandler)
    print(f'Prometheus exporter started on port {port}')
    print(f'Metrics available at http://0.0.0.0:{port}/metrics')
    
    # 백그라운드에서 시스템 메트릭 업데이트
    import threading
    def update_metrics():
        while True:
            update_system_metrics()
            time.sleep(10)
    
    thread = threading.Thread(target=update_metrics, daemon=True)
    thread.start()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Exporter stopped')
        server.shutdown()

if __name__ == '__main__':
    port = int(os.getenv('EXPORTER_PORT', '9090'))
    run_exporter(port)