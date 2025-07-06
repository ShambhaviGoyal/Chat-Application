import os
import random
import logging
from datetime import datetime
from typing import Dict

from flask import (
    Flask, render_template, request, session, jsonify,
    redirect, url_for, flash
)
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)

# ----- Configuration -----
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///chat_users.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CHAT_ROOMS = [
        'Open Mic',
        'Code & Coffee',
        'XP Zone',
        'Study Squad',
        'Lo-Fi Corner',
        'Meme Stream',
        'Wellness Wave'
    ]

# ----- App & Extensions Initialization -----
app = Flask(__name__)
app.config.from_object(Config)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

socketio = SocketIO(
    app,
    cors_allowed_origins=app.config['CORS_ORIGINS'],
    logger=True,
    engineio_logger=True
)

# ----- Logging -----
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ----- Models -----
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ----- In-memory storage -----
active_users: Dict[str, dict] = {}
typing_users: Dict[str, set] = {}
chat_history: Dict[str, list] = {}

# ----- Routes -----
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('signup'))
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('signup'))

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Account created! Please log in.')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid email or password')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    username = current_user.username
    return render_template(
        'index.html',
        username=username,
        rooms=app.config['CHAT_ROOMS']
    )

# ----- SocketIO Events -----
@socketio.on('connect')
def handle_connect():
    if not current_user.is_authenticated:
        logger.warning("Unauthorized connection attempt rejected")
        return False

    username = current_user.username
    active_users[request.sid] = {
        'username': username,
        'connected_at': datetime.now().isoformat()
    }

    emit('active_users', {
        'users': [user['username'] for user in active_users.values()]
    }, broadcast=True)

    logger.info(f"User connected: {username}")

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in active_users:
        username = active_users[request.sid]['username']
        del active_users[request.sid]

        emit('active_users', {
            'users': [user['username'] for user in active_users.values()]
        }, broadcast=True)

        logger.info(f"User disconnected: {username}")

@socketio.on('join')
def on_join(data):
    try:
        username = current_user.username
        room = data['room']

        if room not in app.config['CHAT_ROOMS']:
            logger.warning(f"Invalid room join attempt: {room}")
            return

        join_room(room)
        active_users[request.sid]['room'] = room

        emit('status', {
            'msg': f'{username} has joined the room.',
            'type': 'join',
            'timestamp': datetime.now().isoformat()
        }, room=room)

        if room in chat_history:
            emit('chat_history', {
                'room': room,
                'messages': chat_history[room]
            }, room=request.sid)

        logger.info(f"User {username} joined room: {room}")

    except Exception as e:
        logger.error(f"Join room error: {str(e)}")

@socketio.on('leave')
def on_leave(data):
    try:
        username = current_user.username
        room = data['room']

        leave_room(room)
        if request.sid in active_users:
            active_users[request.sid].pop('room', None)

        emit('status', {
            'msg': f'{username} has left the room.',
            'type': 'leave',
            'timestamp': datetime.now().isoformat()
        }, room=room)

        logger.info(f"User {username} left room: {room}")

    except Exception as e:
        logger.error(f"Leave room error: {str(e)}")

@socketio.on('message')
def handle_message(data):
    try:
        username = current_user.username
        room = data.get('room', 'General')
        msg_type = data.get('type', 'message')
        message = data.get('msg', '').strip()

        if not message:
            return

        timestamp = datetime.now().isoformat()

        if msg_type == 'private':
            target_user = data.get('target')
            if not target_user:
                return

            for sid, user_data in active_users.items():
                if user_data['username'] == target_user:
                    emit('private_message', {
                        'msg': message,
                        'from': username,
                        'to': target_user,
                        'timestamp': timestamp
                    }, room=sid)
                    logger.info(f"Private message sent: {username} -> {target_user}")
                    return

            logger.warning(f"Private message failed - user not found: {target_user}")

        else:
            if room not in app.config['CHAT_ROOMS']:
                logger.warning(f"Message to invalid room: {room}")
                return

            if room not in chat_history:
                chat_history[room] = []

            chat_history[room].append({
                'msg': message,
                'username': username,
                'timestamp': timestamp,
                'reactions': {}  # Added reactions field
            })

            emit('message', {
                'msg': message,
                'username': username,
                'room': room,
                'timestamp': timestamp,
                'reactions': {}  # Send empty reactions initially
            }, room=room)

            logger.info(f"Message sent in {room} by {username}")

    except Exception as e:
        logger.error(f"Message handling error: {str(e)}")

@socketio.on('react_to_message')
def handle_reaction(data):
    try:
        room = data['room']
        msg_index = data['index']
        emoji = data['emoji']
        user = current_user.username

        if room in chat_history and 0 <= msg_index < len(chat_history[room]):
            message = chat_history[room][msg_index]
            reactions = message.get('reactions', {})

            if emoji not in reactions:
                reactions[emoji] = []

            if user in reactions[emoji]:
                # Toggle reaction off
                reactions[emoji].remove(user)
                if not reactions[emoji]:
                    del reactions[emoji]
            else:
                reactions.setdefault(emoji, []).append(user)

            # Save back the updated reactions
            message['reactions'] = reactions

            emit('reaction_update', {
                'index': msg_index,
                'reactions': reactions
            }, room=room)
    except Exception as e:
        logger.error(f"Reaction handling error: {str(e)}")

@socketio.on('typing')
def handle_typing(data):
    username = current_user.username
    room = data['room']
    typing = data['typing']

    if room not in typing_users:
        typing_users[room] = set()

    if typing:
        typing_users[room].add(username)
    else:
        typing_users[room].discard(username)

    users_typing = typing_users[room] - {username}

    if len(users_typing) == 0:
        msg = ''
    elif len(users_typing) == 1:
        msg = f"{list(users_typing)[0]} is typing..."
    elif len(users_typing) == 2:
        u1, u2 = list(users_typing)
        msg = f"{u1} and {u2} are typing..."
    else:
        msg = "Several people are typing..."

    emit('status', {
        'msg': msg,
        'type': 'typing',
        'room': room
    }, room=room)

# ----- Create DB -----
with app.app_context():
    db.create_all()

# ----- Run App -----
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=app.config['DEBUG'],
        use_reloader=app.config['DEBUG']
    )
