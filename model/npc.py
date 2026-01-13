from __init__ import db
from datetime import datetime


class Npc(db.Model):
    __tablename__ = 'npcs'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    is_gas_holder = db.Column(db.Boolean, nullable=False, default=False)

    def __init__(self, name: str, is_gas_holder: bool = False):
        self.name = name
        self.is_gas_holder = is_gas_holder

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "is_gas_holder": self.is_gas_holder,
        }


class QuestionPool(db.Model):
    __tablename__ = 'question_pool'

    id = db.Column(db.Integer, primary_key=True)
    npc_id = db.Column(db.Integer, db.ForeignKey('npcs.id'), nullable=True)
    question_text = db.Column(db.Text, nullable=False)

    npc = db.relationship('Npc', backref=db.backref('questions', cascade='all, delete-orphan'))

    def __init__(self, question_text: str, npc_id: int | None = None):
        self.question_text = question_text
        self.npc_id = npc_id

    def to_dict(self):
        return {
            "id": self.id,
            "npc_id": self.npc_id,
            "question_text": self.question_text,
        }


class NpcInteraction(db.Model):
    __tablename__ = 'npc_interactions'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    session_id = db.Column(db.String(128), nullable=False, index=True)
    npc_id = db.Column(db.Integer, db.ForeignKey('npcs.id'), nullable=False, index=True)
    was_gas_holder = db.Column(db.Boolean, nullable=False, default=False)

    # What happened in this interaction
    interaction_type = db.Column(db.String(32), nullable=False)  # 'question' | 'success'
    question_id = db.Column(db.Integer, db.ForeignKey('question_pool.id'), nullable=True)

    npc = db.relationship('Npc', backref=db.backref('interactions', cascade='all, delete-orphan'))
    question = db.relationship('QuestionPool')

    def __init__(
        self,
        session_id: str,
        npc_id: int,
        was_gas_holder: bool,
        interaction_type: str,
        question_id: int | None = None,
    ):
        self.session_id = session_id
        self.npc_id = npc_id
        self.was_gas_holder = was_gas_holder
        self.interaction_type = interaction_type
        self.question_id = question_id

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "session_id": self.session_id,
            "npc_id": self.npc_id,
            "was_gas_holder": self.was_gas_holder,
            "interaction_type": self.interaction_type,
            "question_id": self.question_id,
        }


def initNpc():
    db.create_all()
