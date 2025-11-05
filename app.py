import os
from flask import Flask, Response
from flask_restful import Api
from flask_cors import CORS
from api.exercise_recommendation import RecommendExercise

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}})
api = Api(app)

# api.add_resource(클래스, "도메인")

api.add_resource(RecommendExercise, '/recommendExercise')


if __name__ == '__main__':
    # app.run(debug=True)
    app.run(host='0.0.0.0', port=5000)