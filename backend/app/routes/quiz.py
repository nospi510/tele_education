from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db, socketio
from app.models.quiz import Quiz
from app.models.quiz_response import QuizResponse
from app.models.session import Session, SessionStatus
from app.models.user import User, UserRole
from flasgger import swag_from
from datetime import datetime

quiz_bp = Blueprint("quiz", __name__)

@quiz_bp.route("/<int:session_id>/create", methods=["POST"])
@jwt_required()
@swag_from({
    "tags": ["Quiz"],
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
                    "question": {"type": "string", "example": "Quelle est la capitale de la France ?"},
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "example": ["Paris", "Lyon", "Marseille", "Toulouse"]
                    },
                    "correct_answer": {"type": "string", "example": "Paris"}
                },
                "required": ["question", "options", "correct_answer"]
            }
        }
    ],
    "responses": {
        "201": {"description": "Quiz créé avec succès"},
        "400": {"description": "Requête invalide ou session non active"},
        "403": {"description": "Seul le professeur peut créer un quiz"},
        "404": {"description": "Session non trouvée"}
    }
})
def create_quiz(session_id):
    current_user_id = get_jwt_identity()
    session = Session.query.get_or_404(session_id)

    if session.professor_id != int(current_user_id):
        return jsonify({"message": "Seul le professeur peut créer un quiz"}), 403

    if session.status != SessionStatus.ACTIVE:
        return jsonify({"message": "Session non active"}), 400

    data = request.get_json()
    if not all(k in data for k in ("question", "options", "correct_answer")):
        return jsonify({"message": "Champs requis manquants"}), 400

    quiz = Quiz(
        session_id=session_id,
        question=data["question"],
        options=data["options"],
        correct_answer=data["correct_answer"],
        created_at=datetime.utcnow()
    )
    db.session.add(quiz)
    db.session.commit()

    socketio.emit("new_quiz", {
        "quiz_id": quiz.id,
        "session_id": session_id,
        "question": quiz.question,
        "options": quiz.options,
        "created_at": quiz.created_at.isoformat()
    }, room=str(session_id))

    return jsonify({"message": "Quiz créé avec succès", "quiz_id": quiz.id}), 201

@quiz_bp.route("/<int:session_id>/<int:quiz_id>/respond", methods=["POST"])
def respond_quiz(session_id, quiz_id):
    session = Session.query.get_or_404(session_id)
    quiz = Quiz.query.get_or_404(quiz_id)

    if session.status != SessionStatus.ACTIVE:
        return jsonify({"message": "Session non active"}), 400

    data = request.get_json()
    if "answer" not in data:
        return jsonify({"message": "Réponse manquante"}), 400

    user_id = get_jwt_identity() if request.headers.get("Authorization") else None
    response = QuizResponse(
        quiz_id=quiz_id,
        user_id=int(user_id) if user_id else None,
        answer=data["answer"],
        submitted_at=datetime.utcnow()
    )
    db.session.add(response)
    db.session.commit()

    socketio.emit("quiz_response", {
        "quiz_id": quiz_id,
        "user_id": user_id,
        "user_name": User.query.get(int(user_id)).name if user_id else "Anonyme",
        "answer": response.answer,
        "submitted_at": response.submitted_at.isoformat()
    }, room=str(session.professor_id))

    return jsonify({"message": "Réponse enregistrée avec succès"}), 201