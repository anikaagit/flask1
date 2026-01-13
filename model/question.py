from __init__ import db


class Question(db.Model):
    __tablename__ = 'question_pool'

    # Existing DBs use `id` as the primary key column.
    id = db.Column(db.Integer, primary_key=True)

    question_text = db.Column(db.Text, nullable=False)
    difficulty_level = db.Column(db.Integer, nullable=True)

    # For MCQ this can be the exact option text or a key like 'A'
    correct_answer = db.Column(db.String(255), nullable=False)

    # JSON array of options
    options = db.Column(db.JSON, nullable=False)

    category = db.Column(db.String(120), nullable=True)
    college_board_aligned = db.Column(db.Boolean, nullable=False, default=False)

    def __init__(
        self,
        question_text: str,
        correct_answer: str,
        options: list,
        difficulty_level: int | None = None,
        category: str | None = None,
        college_board_aligned: bool = False,
    ):
        self.question_text = question_text
        self.correct_answer = correct_answer
        self.options = options
        self.difficulty_level = difficulty_level
        self.category = category
        self.college_board_aligned = college_board_aligned

    def to_public_dict(self):
        return {
            "question_id": self.id,
            "question_text": self.question_text,
            "difficulty_level": self.difficulty_level,
            "options": self.options,
            "category": self.category,
            "college_board_aligned": self.college_board_aligned,
        }

    def to_dict(self):
        # Internal use only; avoid sending correct_answer to clients unless intended
        return {
            **self.to_public_dict(),
            "correct_answer": self.correct_answer,
        }
