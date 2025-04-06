from datetime import datetime
from flask_socketio import SocketIO, emit, join_room, leave_room
from app import socketio,db
from app.models.user import User, UserRole
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.session import Session, SessionStatus
from app.models.hand_request import HandRequest, HandStatus
from app.models.comment import Comment


@socketio.on("connect")
@jwt_required()
def handle_connect():
    """Gérer la connexion d’un client WebSocket."""
    current_user = get_jwt_identity()
    emit("connection_response", {"message": f"User {current_user['id']} connected"})

@socketio.on("join_session")
@jwt_required()
def join_session(data):
    """Rejoindre une session pour recevoir des mises à jour en temps réel."""
    session_id = data.get("session_id")
    session = Session.query.get_or_404(session_id)
    
    join_room(str(session_id))
    emit("session_joined", {"message": f"Joined session {session_id}"}, room=str(session_id))

@socketio.on("leave_session")
@jwt_required()
def leave_session(data):
    """Quitter une session."""
    session_id = data.get("session_id")
    leave_room(str(session_id))
    emit("session_left", {"message": f"Left session {session_id}"}, to=str(session_id))

@socketio.on("post_comment")
@jwt_required()
def handle_post_comment(data):
    """Émettre un commentaire en temps réel à tous les participants de la session."""
    session_id = data.get("session_id")
    content = data.get("content")
    current_user = get_jwt_identity()
    user = User.query.get(current_user["id"])
    session = Session.query.get_or_404(session_id)

    if session.status != SessionStatus.ACTIVE:
        emit("error", {"message": "Session is not active"})
        return

    comment = Comment(session_id=session_id, user_id=user.id, content=content)
    db.session.add(comment)
    db.session.commit()

    emit("new_comment", {
        "id": comment.id,
        "content": comment.content,
        "user_name": user.name,
        "created_at": comment.created_at.isoformat()
    }, room=str(session_id))

@socketio.on("raise_hand")
@jwt_required()
def handle_raise_hand(data):
    """Émettre une demande de main en temps réel au professeur."""
    session_id = data.get("session_id")
    current_user = get_jwt_identity()
    user = User.query.get(current_user["id"])
    session = Session.query.get_or_404(session_id)

    if user.role == UserRole.PROFESSOR or session.status != SessionStatus.ACTIVE:
        emit("error", {"message": "Invalid request"})
        return

    hand_request = HandRequest(session_id=session_id, user_id=user.id, status=HandStatus.PENDING)
    db.session.add(hand_request)
    db.session.commit()

    emit("new_hand_request", {
        "id": hand_request.id,
        "user_id": user.id,
        "user_name": user.name,
        "requested_at": hand_request.requested_at.isoformat()
    }, room=str(session_id), to=str(session.professor_id))

@socketio.on("grant_hand")
@jwt_required()
def handle_grant_hand(data):
    """Émettre un événement lorsque la main est accordée et basculer le flux vidéo."""
    session_id = data.get("session_id")
    request_id = data.get("request_id")
    current_user = get_jwt_identity()
    session = Session.query.get_or_404(session_id)

    if session.professor_id != current_user["id"]:
        emit("error", {"message": "Only the professor can grant the hand"})
        return

    hand_request = HandRequest.query.get_or_404(request_id)
    if hand_request.session_id != session_id or hand_request.status != HandStatus.PENDING:
        emit("error", {"message": "Invalid request"})
        return

    # Révoquer toute main existante
    current_granted = HandRequest.query.filter_by(session_id=session_id, status=HandStatus.GRANTED).first()
    if current_granted:
        current_granted.status = HandStatus.REVOKED
        db.session.commit()
        emit("stream_switch", {"user_id": session.professor_id, "message": "Reverting to professor stream"}, room=str(session_id))

    # Accorder la main
    hand_request.status = HandStatus.GRANTED
    hand_request.granted_at = datetime.utcnow()
    db.session.commit()

    emit("hand_granted", {
        "request_id": hand_request.id,
        "user_id": hand_request.user_id,
        "user_name": hand_request.user.name
    }, room=str(session_id))
    emit("stream_switch", {
        "user_id": hand_request.user_id,
        "message": "Switching to viewer stream"
    }, room=str(session_id))

@socketio.on("revoke_hand")
@jwt_required()
def handle_revoke_hand(data):
    """Émettre un événement lorsque la main est révoquée et revenir au flux du professeur."""
    session_id = data.get("session_id")
    request_id = data.get("request_id")
    current_user = get_jwt_identity()
    session = Session.query.get_or_404(session_id)

    if session.professor_id != current_user["id"]:
        emit("error", {"message": "Only the professor can revoke the hand"})
        return

    hand_request = HandRequest.query.get_or_404(request_id)
    if hand_request.session_id != session_id or hand_request.status != HandStatus.GRANTED:
        emit("error", {"message": "Invalid request"})
        return

    hand_request.status = HandStatus.REVOKED
    db.session.commit()

    emit("hand_revoked", {
        "request_id": hand_request.id,
        "user_id": hand_request.user_id,
        "user_name": hand_request.user.name
    }, room=str(session_id))
    emit("stream_switch", {
        "user_id": session.professor_id,
        "message": "Switching back to professor stream"
    }, room=str(session_id))

@socketio.on("end_session")
@jwt_required()
def handle_end_session(data):
    """Émettre un événement lorsque la session se termine et arrêter le streaming."""
    session_id = data.get("session_id")
    current_user = get_jwt_identity()
    session = Session.query.get_or_404(session_id)

    if session.professor_id != current_user["id"]:
        emit("error", {"message": "Only the professor can end the session"})
        return

    session.status = SessionStatus.ENDED
    session.end_time = datetime.utcnow()
    db.session.commit()

    emit("session_ended", {
        "session_id": session_id,
        "title": session.title
    }, room=str(session_id))
    emit("stream_stop", {"message": "Session ended, streaming stopped"}, room=str(session_id))