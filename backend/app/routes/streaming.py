from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db, socketio
from app.models.session import Session, SessionStatus
from app.models.user import User, UserRole
from flasgger import swag_from
import redis
from app.config import Config

streaming_bp = Blueprint("streaming", __name__)
redis_client = redis.from_url(Config.REDIS_URL)

@streaming_bp.route("/<int:session_id>/start", methods=["POST"])
@jwt_required()
@swag_from({
    "tags": ["Streaming"],
    "security": [{"Bearer": []}],
    "parameters": [
        {
            "name": "session_id",
            "in": "path",
            "type": "integer",
            "required": True,
            "description": "ID de la session"
        }
    ],
    "responses": {
        "200": {"description": "Streaming démarré, fichier M3U8 généré"},
        "400": {"description": "Session non active ou requête invalide"},
        "403": {"description": "Seul le professeur peut démarrer le streaming"},
        "404": {"description": "Session non trouvée"}
    }
})
def start_streaming(session_id):
    current_user_id = get_jwt_identity()
    session = Session.query.get_or_404(session_id)

    if session.professor_id != int(current_user_id):
        return jsonify({"message": "Seul le professeur peut démarrer le streaming"}), 403

    if session.status != SessionStatus.ACTIVE:
        return jsonify({"message": "Session non active"}), 400

    stream_key = f"live/session_{session_id}"
    webrtc_url = f"http://localhost:1985/rtc/v1/publish/"
    m3u8_url = f"http://localhost:8080/hls/{stream_key}.m3u8"

    # Stocker l'état du streaming dans Redis
    redis_client.setex(f"stream:{session_id}", 3600, m3u8_url)  # Expire après 1 heure
    session.stream_url = m3u8_url
    db.session.commit()

    socketio.emit("stream_started", {
        "session_id": session_id,
        "webrtc_url": webrtc_url,
        "m3u8_url": m3u8_url
    }, room=str(session_id))

    return jsonify({
        "message": "Streaming démarré",
        "webrtc_url": webrtc_url,
        "m3u8_url": m3u8_url
    }), 200

@streaming_bp.route("/<int:session_id>/stop", methods=["POST"])
@jwt_required()
@swag_from({
    "tags": ["Streaming"],
    "security": [{"Bearer": []}],
    "parameters": [
        {
            "name": "session_id",
            "in": "path",
            "type": "integer",
            "required": True,
            "description": "ID de la session"
        }
    ],
    "responses": {
        "200": {"description": "Streaming arrêté"},
        "400": {"description": "Session non active ou pas de flux"},
        "403": {"description": "Seul le professeur peut arrêter le streaming"},
        "404": {"description": "Session non trouvée"}
    }
})
def stop_streaming(session_id):
    current_user_id = get_jwt_identity()
    session = Session.query.get_or_404(session_id)

    if session.professor_id != int(current_user_id):
        return jsonify({"message": "Seul le professeur peut arrêter le streaming"}), 403

    if session.status != SessionStatus.ACTIVE:
        return jsonify({"message": "Session non active"}), 400

    # Supprimer l'état du streaming de Redis
    redis_client.delete(f"stream:{session_id}")
    session.stream_url = None
    db.session.commit()

    socketio.emit("stream_stopped", {
        "session_id": session_id,
        "message": "Streaming arrêté"
    }, room=str(session_id))

    return jsonify({"message": "Streaming arrêté"}), 200

@streaming_bp.route("/<int:session_id>/offer", methods=["POST"])
@jwt_required()
@swag_from({
    "tags": ["Streaming"],
    "security": [{"Bearer": []}],
    "parameters": [
        {
            "name": "session_id",
            "in": "path",
            "type": "integer",
            "required": True,
            "description": "ID de la session"
        },
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "properties": {
                    "sdp": {"type": "string", "example": "v=0\no=- ..."},
                    "type": {"type": "string", "example": "offer"}
                },
                "required": ["sdp", "type"]
            }
        }
    ],
    "responses": {
        "200": {"description": "Offre WebRTC enregistrée"},
        "400": {"description": "Requête invalide ou session non active"},
        "403": {"description": "Non autorisé à diffuser"},
        "404": {"description": "Session non trouvée"}
    }
})
def register_offer(session_id):
    current_user = get_jwt_identity()
    session = Session.query.get_or_404(session_id)

    if session.status != SessionStatus.ACTIVE:
        return jsonify({"message": "Session non active"}), 400

    is_professor = int(current_user) == session.professor_id
    if not is_professor:
        return jsonify({"message": "Seul le professeur peut diffuser via WebRTC"}), 403

    data = request.get_json()
    if "sdp" not in data or "type" not in data or data["type"] != "offer":
        return jsonify({"message": "Offre SDP invalide"}), 400

    socketio.emit("stream_offer", {
        "user_id": current_user,
        "user_name": User.query.get(current_user).name,
        "sdp": data["sdp"],
        "type": data["type"]
    }, room=str(session_id))

    return jsonify({"message": "Offre enregistrée, en attente de réponse"}), 200

@streaming_bp.route("/<int:session_id>/answer", methods=["POST"])
@jwt_required()
@swag_from({
    "tags": ["Streaming"],
    "security": [{"Bearer": []}],
    "parameters": [
        {
            "name": "session_id",
            "in": "path",
            "type": "integer",
            "required": True,
            "description": "ID de la session"
        },
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "properties": {
                    "sdp": {"type": "string", "example": "v=0\no=- ..."},
                    "type": {"type": "string", "example": "answer"},
                    "to_user_id": {"type": "integer", "example": 1}
                },
                "required": ["sdp", "type", "to_user_id"]
            }
        }
    ],
    "responses": {
        "200": {"description": "Réponse envoyée avec succès"},
        "400": {"description": "Requête invalide"},
        "404": {"description": "Session non trouvée"}
    }
})
def send_answer(session_id):
    current_user = get_jwt_identity()
    session = Session.query.get_or_404(session_id)

    if session.status != SessionStatus.ACTIVE:
        return jsonify({"message": "Session non active"}), 400

    data = request.get_json()
    if "sdp" not in data or "type" not in data or data["type"] != "answer" or "to_user_id" not in data:
        return jsonify({"message": "Réponse SDP invalide"}), 400

    socketio.emit("stream_answer", {
        "user_id": current_user,
        "sdp": data["sdp"],
        "type": data["type"]
    }, room=str(data["to_user_id"]))

    return jsonify({"message": "Réponse envoyée avec succès"}), 200

@streaming_bp.route("/<int:session_id>/ice-candidate", methods=["POST"])
@jwt_required()
@swag_from({
    "tags": ["Streaming"],
    "security": [{"Bearer": []}],
    "parameters": [
        {
            "name": "session_id",
            "in": "path",
            "type": "integer",
            "required": True,
            "description": "ID de la session"
        },
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "properties": {
                    "candidate": {"type": "string", "example": "candidate:1 1 UDP ..."},
                    "to_user_id": {"type": "integer", "example": 1}
                },
                "required": ["candidate", "to_user_id"]
            }
        }
    ],
    "responses": {
        "200": {"description": "Candidat ICE envoyé avec succès"},
        "400": {"description": "Requête invalide"},
        "404": {"description": "Session non trouvée"}
    }
})
def send_ice_candidate(session_id):
    current_user = get_jwt_identity()
    session = Session.query.get_or_404(session_id)

    if session.status != SessionStatus.ACTIVE:
        return jsonify({"message": "Session non active"}), 400

    data = request.get_json()
    if "candidate" not in data or "to_user_id" not in data:
        return jsonify({"message": "Candidat ICE invalide"}), 400

    socketio.emit("ice_candidate", {
        "user_id": current_user,
        "candidate": data["candidate"]
    }, room=str(data["to_user_id"]))

    return jsonify({"message": "Candidat ICE envoyé avec succès"}), 200