from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.session import Session, SessionStatus
from app.models.user import User, UserRole
from flasgger import swag_from
from datetime import datetime

sessions_bp = Blueprint("sessions", __name__)

@sessions_bp.route("", methods=["POST"])
@jwt_required()
@swag_from({
    "tags": ["Sessions"],
    "security": [{"Bearer": []}],
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "required": True,
            "schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "example": "Math Lesson"},
                    "description": {"type": "string", "example": "Introduction to Algebra"}
                },
                "required": ["title"]
            }
        }
    ],
    "responses": {
        "201": {
            "description": "Session created successfully",
            "schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "title": {"type": "string"},
                    "status": {"type": "string"}
                }
            }
        },
        "400": {"description": "Invalid input"},
        "403": {"description": "Only professors can create sessions"}
    }
})
def create_session():
    current_user = get_jwt_identity()
    if current_user["role"] != "professor":
        return jsonify({"message": "Only professors can create sessions"}), 403

    data = request.get_json()
    if "title" not in data or not data["title"]:
        return jsonify({"message": "Title is required"}), 400

    session = Session(
        title=data["title"],
        description=data.get("description"),
        professor_id=current_user["id"],
        status=SessionStatus.ACTIVE
    )
    db.session.add(session)
    db.session.commit()

    return jsonify({
        "id": session.id,
        "title": session.title,
        "status": session.status.value
    }), 201

@sessions_bp.route("/active", methods=["GET"])
@jwt_required()
@swag_from({
    "tags": ["Sessions"],
    "security": [{"Bearer": []}],
    "responses": {
        "200": {
            "description": "List of active sessions",
            "schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "professor_name": {"type": "string"},
                        "start_time": {"type": "string"}
                    }
                }
            }
        },
        "401": {"description": "Unauthorized"}
    }
})
def get_active_sessions():
    sessions = Session.query.filter_by(status=SessionStatus.ACTIVE).all()
    result = [
        {
            "id": session.id,
            "title": session.title,
            "description": session.description,
            "professor_name": session.professor.name,
            "start_time": session.start_time.isoformat()
        }
        for session in sessions
    ]
    return jsonify(result), 200

@sessions_bp.route("/<int:session_id>", methods=["GET"])
@jwt_required()
@swag_from({
    "tags": ["Sessions"],
    "security": [{"Bearer": []}],
    "parameters": [
        {
            "name": "session_id",
            "in": "path",
            "type": "integer",
            "required": True,
            "description": "ID of the session"
        }
    ],
    "responses": {
        "200": {
            "description": "Session details",
            "schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "professor_name": {"type": "string"},
                    "status": {"type": "string"},
                    "start_time": {"type": "string"},
                    "end_time": {"type": "string"}
                }
            }
        },
        "404": {"description": "Session not found"}
    }
})
def get_session(session_id):
    session = Session.query.get_or_404(session_id)
    return jsonify({
        "id": session.id,
        "title": session.title,
        "description": session.description,
        "professor_name": session.professor.name,
        "status": session.status.value,
        "start_time": session.start_time.isoformat(),
        "end_time": session.end_time.isoformat() if session.end_time else None
    }), 200

@sessions_bp.route("/<int:session_id>", methods=["PUT"])
@jwt_required()
@swag_from({
    "tags": ["Sessions"],
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
                    "title": {"type": "string", "example": "Updated Math Lesson"},
                    "description": {"type": "string", "example": "Updated description"},
                    "status": {"type": "string", "enum": ["active", "paused", "ended"], "example": "ended"}
                }
            }
        }
    ],
    "responses": {
        "200": {"description": "Session updated successfully"},
        "403": {"description": "Only the professor can update the session"},
        "404": {"description": "Session not found"}
    }
})
def update_session(session_id):
    current_user = get_jwt_identity()
    session = Session.query.get_or_404(session_id)

    if session.professor_id != current_user["id"]:
        return jsonify({"message": "Only the professor can update the session"}), 403

    data = request.get_json()
    if "title" in data:
        session.title = data["title"]
    if "description" in data:
        session.description = data["description"]
    if "status" in data:
        session.status = SessionStatus(data["status"])
        if session.status == SessionStatus.ENDED:
            session.end_time = datetime.utcnow()

    db.session.commit()
    return jsonify({"message": "Session updated successfully"}), 200

@sessions_bp.route("/<int:session_id>/end", methods=["POST"])
@jwt_required()
@swag_from({
    "tags": ["Sessions"],
    "security": [{"Bearer": []}],
    "parameters": [
        {
            "name": "session_id",
            "in": "path",
            "type": "integer",
            "required": True,
            "description": "ID of the session"
        }
    ],
    "responses": {
        "200": {"description": "Session ended successfully"},
        "403": {"description": "Only the professor can end the session"},
        "404": {"description": "Session not found"}
    }
})
def end_session(session_id):
    current_user = get_jwt_identity()
    session = Session.query.get_or_404(session_id)

    if session.professor_id != current_user["id"]:
        return jsonify({"message": "Only the professor can end the session"}), 403

    if session.status == SessionStatus.ENDED:
        return jsonify({"message": "Session already ended"}), 400

    session.status = SessionStatus.ENDED
    session.end_time = datetime.utcnow()
    db.session.commit()

    return jsonify({"message": "Session ended successfully"}), 200