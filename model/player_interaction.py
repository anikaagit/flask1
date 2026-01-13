from __init__ import db
from datetime import datetime


class PlayerInteraction(db.Model):
    __tablename__ = 'player_interactions'

    id = db.Column('interaction_id', db.Integer, primary_key=True)

    session_id = db.Column(db.String(64), db.ForeignKey('game_sessions.session_id'), nullable=False, index=True)
    npc_id = db.Column(db.Integer, db.ForeignKey('npcs.id'), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question_pool.id'), nullable=True, index=True)

    user_answer = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, nullable=True)

    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    response_time_ms = db.Column(db.Integer, nullable=True)

    def __init__(
        self,
        session_id: str,
        npc_id: int,
        question_id: int | None = None,
        user_answer: str | None = None,
        is_correct: bool | None = None,
        response_time_ms: int | None = None,
    ):
        self.session_id = session_id
        self.npc_id = npc_id
        self.question_id = question_id
        self.user_answer = user_answer
        self.is_correct = is_correct
        self.response_time_ms = response_time_ms

    def to_dict(self):
        return {
            "interaction_id": self.id,
            "session_id": self.session_id,
            "npc_id": self.npc_id,
            "question_id": self.question_id,
            "user_answer": self.user_answer,
            "is_correct": self.is_correct,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "response_time_ms": self.response_time_ms,
        }
