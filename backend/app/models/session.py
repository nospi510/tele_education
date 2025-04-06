from app import db
from datetime import datetime
import enum

class SessionStatus(enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"

class Session(db.Model):
    __tablename__ = "sessions"
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    professor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.Enum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=True)

    # Relations
    hand_requests = db.relationship("HandRequest", backref="session", lazy=True)
    comments = db.relationship("Comment", backref="session", lazy=True)
    quizzes = db.relationship("Quiz", backref="session", lazy=True)
    resources = db.relationship("Resource", backref="session", lazy=True)

    def __repr__(self):
        return f"<Session {self.title} - {self.status.value}>"