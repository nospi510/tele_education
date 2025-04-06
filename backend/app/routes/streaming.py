from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.session import Session, SessionStatus
from app.models.hand_request import HandRequest, HandStatus
from app.models.user import User, UserRole
from flasgger import swag_from

streaming_bp = Blueprint("streaming", __name__)

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
            "description": "ID of the session"
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
        "200": {"description": "Offer registered, waiting for answer"},
        "400": {"description": "Invalid request or session not active"},
        "403": {"description": "Unauthorized to stream"},
        "404": {"description": "Session not found"}
    }
})
def register_offer(session_id):
    current_user = get_jwt_identity()
    session = Session.query.get_or_404(session_id)

    if session.status != SessionStatus.ACTIVE:
        return jsonify({"message": "Session is not active"}), 400

    is_professor = current_user["id"] == session.professor_id
    has_hand = HandRequest.query.filter_by(session_id=session_id, user_id=current_user["id"], status=HandStatus.GRANTED).first()
    if not (is_professor or has_hand):
        return jsonify({"message": "You are not authorized to stream"}), 403

    data = request.get_json()
    if "sdp" not in data or "type" not in data or data["type"] != "offer":
        return jsonify({"message": "Invalid SDP offer"}), 400

    from app import socketio
    socketio.emit("stream_offer", {
        "user_id": current_user["id"],
        "user_name": User.query.get(current_user["id"]).name,
        "sdp": data["sdp"],
        "type": data["type"]
    }, room=str(session_id))

    return jsonify({"message": "Offer registered, waiting for answer"}), 200

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
            "description": "ID of the session"
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
        "200": {"description": "Answer sent successfully"},
        "400": {"description": "Invalid request"},
        "404": {"description": "Session not found"}
    }
})
def send_answer(session_id):
    current_user = get_jwt_identity()
    session = Session.query.get_or_404(session_id)

    if session.status != SessionStatus.ACTIVE:
        return jsonify({"message": "Session is not active"}), 400

    data = request.get_json()
    if "sdp" not in data or "type" not in data or data["type"] != "answer" or "to_user_id" not in data:
        return jsonify({"message": "Invalid SDP answer"}), 400

    from app import socketio
    socketio.emit("stream_answer", {
        "user_id": current_user["id"],
        "sdp": data["sdp"],
        "type": data["type"]
    }, room=str(data["to_user_id"]))

    return jsonify({"message": "Answer sent successfully"}), 200

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
            "description": "ID of the session"
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
        "200": {"description": "ICE candidate sent successfully"},
        "400": {"description": "Invalid request"},
        "404": {"description": "Session not found"}
    }
})
def send_ice_candidate(session_id):
    current_user = get_jwt_identity()
    session = Session.query.get_or_404(session_id)

    if session.status != SessionStatus.ACTIVE:
        return jsonify({"message": "Session is not active"}), 400

    data = request.get_json()
    if "candidate" not in data or "to_user_id" not in data:
        return jsonify({"message": "Invalid ICE candidate"}), 400

    from app import socketio
    socketio.emit("ice_candidate", {
        "user_id": current_user["id"],
        "candidate": data["candidate"]
    }, room=str(data["to_user_id"]))

    return jsonify({"message": "ICE candidate sent successfully"}), 200