import logging
import os
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify
from flask_restful import Api
from flask_cors import CORS
from api.exercise_recommendation import RecommendExercise

app = Flask(__name__)

log_dir = '/tmp/log/app'
os.makedirs(log_dir, exist_ok=True)

file_handler = RotatingFileHandler(
    os.path.join(log_dir, 'app.log'),
    maxBytes=10485760,  # 10MB
    backupCount=10
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))

app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

CORS(app, resources={r"/*": {"origins": "*"}})
api = Api(app)

api.add_resource(RecommendExercise, '/recommendExercise')

@app.route('/health', methods=['GET'])
def health_check():
    """Kubernetes health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'recommend-service',
        'version': '1.0.0'
    }), 200

if __name__ == '__main__':
    # app.run(debug=True)
    app.run(host='0.0.0.0', port=5000)