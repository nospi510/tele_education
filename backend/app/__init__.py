from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from flask_migrate import Migrate
from flasgger import Swagger
from app.config import Config

db = SQLAlchemy()
jwt = JWTManager()
socketio = SocketIO()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialisation des extensions
    db.init_app(app)
    jwt.init_app(app)
    socketio.init_app(app)
    migrate.init_app(app, db)

    # Configuration pour gérer un dictionnaire comme identité JWT
    @jwt.user_identity_loader
    def user_identity_lookup(user):
        return user  # Permet de passer un dictionnaire comme identity

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        return User.query.get(identity["id"])  # Charge l'utilisateur à partir de l'ID dans le dictionnaire

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

    # Enregistrement des blueprints (routes)
    from app.routes.auth import auth_bp
    from app.routes.sessions import sessions_bp
    from app.routes.hand_raise import hand_raise_bp
    from app.routes.comments import comments_bp
    from app.routes.streaming import streaming_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(sessions_bp, url_prefix='/sessions')
    app.register_blueprint(hand_raise_bp, url_prefix='/sessions')
    app.register_blueprint(comments_bp, url_prefix='/sessions')
    app.register_blueprint(streaming_bp, url_prefix='/sessions')

    # Enregistrement des événements WebSocket
    from app.sockets import events

    return app