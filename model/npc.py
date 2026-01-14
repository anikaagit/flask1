from __init__ import db
from sqlalchemy import text


class Npc(db.Model):
    __tablename__ = 'npcs'

    # NOTE: existing deployments already have `id` as the primary key column.
    # We keep `id` for compatibility and expose it to clients as `npc_id`.
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    dialogue_text = db.Column(db.Text, nullable=True)

    # Gas holder is assigned per-session; this field is kept for compatibility.
    is_gas_holder = db.Column(db.Boolean, nullable=False, default=False)

    def __init__(
        self,
        name: str,
        description: str | None = None,
        dialogue_text: str | None = None,
        is_gas_holder: bool = False,
    ):
        self.name = name
        self.description = description
        self.dialogue_text = dialogue_text
        self.is_gas_holder = is_gas_holder

    def to_public_dict(self):
        # IMPORTANT: do not reveal gas holder assignment in game/start
        return {
            "npc_id": self.id,
            "name": self.name,
            "description": self.description,
            "dialogue_text": self.dialogue_text,
        }

    def to_dict(self):
        return {
            **self.to_public_dict(),
            "is_gas_holder": self.is_gas_holder,
        }


def initGasGame():
    db.create_all()

    # Lightweight, best-effort schema upgrades for SQLite (no Alembic migrations in this repo).
    # This keeps existing DBs (which may already have npcs/question_pool) compatible.
    try:
        if db.engine.dialect.name == 'sqlite':
            npc_cols = {row[1] for row in db.session.execute(text('PRAGMA table_info(npcs)')).fetchall()}
            if 'description' not in npc_cols:
                db.session.execute(text('ALTER TABLE npcs ADD COLUMN description TEXT'))
            if 'dialogue_text' not in npc_cols:
                db.session.execute(text('ALTER TABLE npcs ADD COLUMN dialogue_text TEXT'))

            q_cols = {row[1] for row in db.session.execute(text('PRAGMA table_info(question_pool)')).fetchall()}
            if 'difficulty_level' not in q_cols:
                db.session.execute(text('ALTER TABLE question_pool ADD COLUMN difficulty_level INTEGER'))
            if 'correct_answer' not in q_cols:
                db.session.execute(text('ALTER TABLE question_pool ADD COLUMN correct_answer VARCHAR(255)'))
            if 'options' not in q_cols:
                db.session.execute(text('ALTER TABLE question_pool ADD COLUMN options JSON'))
            if 'category' not in q_cols:
                db.session.execute(text('ALTER TABLE question_pool ADD COLUMN category VARCHAR(120)'))
            if 'college_board_aligned' not in q_cols:
                db.session.execute(text('ALTER TABLE question_pool ADD COLUMN college_board_aligned BOOLEAN DEFAULT 0'))

            # Indexes for common analytics lookups
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_game_sessions_user_id ON game_sessions (user_id)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_game_sessions_start_time ON game_sessions (start_time)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_player_interactions_session_id ON player_interactions (session_id)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_player_interactions_question_id ON player_interactions (question_id)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_player_interactions_timestamp ON player_interactions (timestamp)'))

            db.session.commit()
    except Exception:
        db.session.rollback()

    # Lightweight seed so the game can run locally without extra scripts.
    # Ensure there are enough NPCs/questions for the minigame.
    try:
        from model.question import Question

        # Seed/extend NPCs up to 5 minimum (the Gas Hunt frontend expects 5).
        existing_npcs = Npc.query.order_by(Npc.id.asc()).all()
        existing_names = {n.name for n in existing_npcs}

        npc_candidates = [
            Npc(name='Test Gas Holder', description='Debug NPC.', dialogue_text='Ask me a question.'),
            Npc(name='Test Friendly NPC', description='Debug NPC.', dialogue_text='Hello there!'),
            Npc(name='Gas Station Attendant', description='Works the counter.', dialogue_text='Need some fuel?'),
            Npc(name='Road Tripper', description='Traveling across town.', dialogue_text='I just need directions.'),
            Npc(name='Mechanic', description='Fixes cars for a living.', dialogue_text='Sounds like an engine issue.'),
            Npc(name='Delivery Driver', description='In a hurry.', dialogue_text='Running late on my route.'),
            Npc(name='Tourist', description='New in town.', dialogue_text='Where is the nearest landmark?'),
        ]

        to_add = []
        for candidate in npc_candidates:
            if len(existing_npcs) + len(to_add) >= 5:
                break
            if candidate.name in existing_names:
                continue
            to_add.append(candidate)
            existing_names.add(candidate.name)

        if to_add:
            db.session.add_all(to_add)
            db.session.commit()

        valid_question_exists = (
            Question.query
            .filter(Question.correct_answer.isnot(None))
            .filter(Question.options.isnot(None))
            .first()
            is not None
        )

        if not valid_question_exists:
            db.session.add_all([
                Question(
                    question_text='Which of these best describes an algorithm?',
                    correct_answer='A step-by-step procedure to solve a problem',
                    options=[
                        'A programming language',
                        'A step-by-step procedure to solve a problem',
                        'A computer hardware component',
                        'A type of network protocol'
                    ],
                    difficulty_level=1,
                    category='APCSP',
                    college_board_aligned=True,
                ),
                Question(
                    question_text='What does a boolean variable represent?',
                    correct_answer='True/False',
                    options=['0-9', 'A sentence', 'True/False', 'A picture'],
                    difficulty_level=1,
                    category='APCSP',
                    college_board_aligned=True,
                ),
            ])
            db.session.commit()
    except Exception:
        db.session.rollback()
