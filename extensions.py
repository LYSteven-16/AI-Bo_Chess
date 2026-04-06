from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

db = SQLAlchemy()
socketio = SocketIO()

CURRENT_USER_ID = 1
CURRENT_USER_NAME = '游客'
