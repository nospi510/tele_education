from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_migrate import Migrate
from flasgger import Swagger
from app.config import Config

db = SQLAlchemy()
jwt = JWTManager()
socketio = SocketIO(cors_allowed_origins="*")
migrate = Migrate()

def create_app():
    app = Flask(__name__, template_folder='templates')
    app.config.from_object(Config)

    # Initialisation des extensions
    db.init_app(app)
    jwt.init_app(app)
    socketio.init_app(app, async_mode='eventlet', cors_allowed_origins="*")
    migrate.init_app(app, db)

    # Configuration de Flasgger avec support Bearer Token
    app.config['SWAGGER'] = {
        'title': 'HbbTV Application API',
        'uiversion': 3,
        'description': 'API pour une application HbbTV avec interactions en direct',
        'specs_route': '/apidocs/',
        'securityDefinitions': {
            'Bearer': {
                'type': 'apiKey',
                'name': 'Authorization',
                'in': 'header',
                'description': 'Enter your JWT token with "Bearer " prefix (e.g., "Bearer <token>")'
            }
        },
        'security': [{'Bearer': []}]
    }
    Swagger(app)

    # Enregistrement des blueprints
    from app.routes.auth import auth_bp
    from app.routes.sessions import sessions_bp
    from app.routes.hand_raise import hand_raise_bp
    from app.routes.comments import comments_bp
    from app.routes.streaming import streaming_bp
    from app.routes.quiz import quiz_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(sessions_bp, url_prefix='/sessions')
    app.register_blueprint(hand_raise_bp, url_prefix='/sessions')
    app.register_blueprint(comments_bp, url_prefix='/sessions')
    app.register_blueprint(streaming_bp, url_prefix='/sessions')
    app.register_blueprint(quiz_bp, url_prefix='/sessions')

    # Enregistrement des événements WebSocket
    with app.app_context():
        from app.models.session import Session
        from flask_jwt_extended import decode_token
        from flask_socketio import join_room, emit
        from datetime import datetime

        @socketio.on("connect")
        def handle_connect(auth):
            if not auth or 'token' not in auth:
                raise ConnectionRefusedError("Missing token")
            token = auth['token']
            if token.startswith("Bearer "):
                token = token[7:]
            try:
                decode_token(token)
                # Stocker le token dans l'environnement de la session Socket.IO
                socketio.server.environ[request.sid] = {'token': token}
            except Exception as e:
                raise ConnectionRefusedError("Invalid token")

        @socketio.on("join_session")
        def handle_join_session(data):
            session_id = data.get("session_id")
            if not session_id:
                raise ConnectionRefusedError("Missing session_id")
            # Récupérer le token depuis l'environnement Socket.IO
            environ = socketio.server.environ.get(request.sid, {})
            token = environ.get('token')
            if not token:
                raise ConnectionRefusedError("Missing token")
            try:
                decode_token(token)
                join_room(str(session_id))
                session_obj = Session.query.get(session_id)
                if session_obj and session_obj.stream_url:
                    emit("session_joined", {"stream_url": session_obj.stream_url}, to=str(session_id))
            except Exception as e:
                raise ConnectionRefusedError("Invalid token")

        @socketio.on("post_comment")
        def handle_comment(data):
            session_id = data.get("session_id")
            content = data.get("content")
            if session_id and content:
                emit("new_comment", {
                    "user_name": "Utilisateur",  # À remplacer par le nom réel
                    "content": content,
                    "created_at": datetime.utcnow().isoformat()
                }, room=str(session_id))

    return app