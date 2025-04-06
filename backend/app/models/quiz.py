from app import db
from datetime import datetime

class Quiz(db.Model):
    __tablename__ = "quizzes"
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False)
    question = db.Column(db.Text, nullable=False)
    options = db.Column(db.JSON, nullable=False)
    correct_answer = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relation
    responses = db.relationship("QuizResponse", backref="quiz", lazy=True)

    def __repr__(self):
        return f"<Quiz {self.question[:20]}>"