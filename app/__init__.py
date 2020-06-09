from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:5000","https://preshot.app"])

from app import views