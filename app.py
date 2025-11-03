import os
from flask import Flask, Response
from flask_restful import Api
from flask_cors import CORS

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}})
api = Api(app)

# api.add_resource(클래스, "도메인")