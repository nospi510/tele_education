from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.session import Session, SessionStatus
from app.models.user import User, UserRole
from flasgger import swag_from
from datetime import datetime

sessions_bp = Blueprint("sessions", __name__)

@sessions_bp.route("/create", methods=["GET"])
def create_session_page():
    if not session.get("user_id") or session.get("role") != "professor":
        return redirect("/auth/login")
    user_id = session.get("user_id")
    existing_sessions = Session.query.filter_by(professor_id=user_id, status=SessionStatus.ACTIVE).all()
    return render_template("create_session.html", existing_sessions=existing_sessions)

@sessions_bp.route("/professor", methods=["GET"])
def professor_page():
    if not session.get("user_id") or session.get("role") != "professor":
        return redirect("/auth/login")
    session_id = request.args.get("session_id", type=int)
    if not session_id:
        return redirect("/sessions/active")
    session_obj = Session.query.get(session_id)
    if not session_obj:
        return redirect("/sessions/active")
    if session_obj.professor_id != session.get("user_id"):
        return jsonify({"message": "Vous n'êtes pas le professeur de cette session"}), 403
    return render_template("professor.html", session_id=session_id)

@sessions_bp.route("/viewer", methods=["GET"])
def viewer_page():
    session_id = request.args.get("session_id", type=int)
    if not session_id:
        return redirect("/sessions/active")
    session_obj = Session.query.get(session_id)
    if not session_obj:
        return redirect("/sessions/active")
    return render_template("viewer.html", session_id=session_id)

@sessions_bp.route("/active", methods=["GET"])
def select_session_page():
    if not session.get("user_id"):
        return redirect("/auth/login")
    sessions = Session.query.filter_by(status=SessionStatus.ACTIVE).all()
    return render_template("select_session.html", sessions=sessions)

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
        "401": {"description": "Unauthorized"},
        "403": {"description": "Only professors can create sessions"}
    }
})
def create_session():
    current_user_id = get_jwt_identity()
    user = User.query.get(int(current_user_id))
    if user.role != UserRole.PROFESSOR:
        return jsonify({"message": "Only professors can create sessions"}), 403

    data = request.get_json()
    if "title" not in data or not data["title"]:
        return jsonify({"message": "Title is required"}), 400

    session_obj = Session(
        title=data["title"],
        description=data.get("description"),
        professor_id=int(current_user_id),
        status=SessionStatus.ACTIVE
    )
    db.session.add(session_obj)
    db.session.commit()

    return jsonify({
        "id": session_obj.id,
        "title": session_obj.title,
        "status": session_obj.status.value
    }), 201

@sessions_bp.route("/active", methods=["GET"])
@swag_from({
    "tags": ["Sessions"],
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
        }
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
        "401": {"description": "Unauthorized"},
        "404": {"description": "Session not found"}
    }
})
def get_session(session_id):
    session_obj = Session.query.get_or_404(session_id)
    return jsonify({
        "id": session_obj.id,
        "title": session_obj.title,
        "description": session_obj.description,
        "professor_name": session_obj.professor.name,
        "status": session_obj.status.value,
        "start_time": session_obj.start_time.isoformat(),
        "end_time": session_obj.end_time.isoformat() if session_obj.end_time else None
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
        "401": {"description": "Unauthorized"},
        "403": {"description": "Only the professor can update the session"},
        "404": {"description": "Session not found"}
    }
})
def update_session(session_id):
    current_user_id = get_jwt_identity()
    session_obj = Session.query.get_or_404(session_id)

    if session_obj.professor_id != int(current_user_id):
        return jsonify({"message": "Only the professor can update the session"}), 403

    data = request.get_json()
    if "title" in data:
        session_obj.title = data["title"]
    if "description" in data:
        session_obj.description = data["description"]
    if "status" in data:
        session_obj.status = SessionStatus(data["status"])
        if session_obj.status == SessionStatus.ENDED:
            session_obj.end_time = datetime.utcnow()

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
        "401": {"description": "Unauthorized"},
        "403": {"description": "Only the professor can end the session"},
        "404": {"description": "Session not found"}
    }
})
def end_session(session_id):
    current_user_id = get_jwt_identity()
    session_obj = Session.query.get_or_404(session_id)

    if session_obj.professor_id != int(current_user_id):
        return jsonify({"message": "Only the professor can end the session"}), 403

    if session_obj.status == SessionStatus.ENDED:
        return jsonify({"message": "Session already ended"}), 400

    session_obj.status = SessionStatus.ENDED
    session_obj.end_time = datetime.utcnow()
    db.session.commit()

    return jsonify({"message": "Session ended successfully"}), 200