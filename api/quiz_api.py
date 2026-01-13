from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify

from __init__ import db
from model.game_session import GameSession
from model.question import Question
from model.player_interaction import PlayerInteraction


quiz_api = Blueprint('quiz_api', __name__, url_prefix='/api/quiz')

SESSION_TIMEOUT_MINUTES = 30


def _normalize(val: str | None) -> str:
    return (val or '').strip().lower()


def _is_session_expired(session: GameSession) -> bool:
    if not session or session.is_completed:
        return False
    if not session.start_time:
        return False
    return datetime.utcnow() - session.start_time > timedelta(minutes=SESSION_TIMEOUT_MINUTES)


@quiz_api.route('/answer', methods=['POST'])
def answer():
    data = request.get_json(silent=True) or {}

    session_id = data.get('session_id')
    question_id_raw = data.get('question_id')
    user_answer = data.get('user_answer')
    response_time_ms = data.get('response_time_ms')

    if not session_id or question_id_raw is None or user_answer is None:
        return jsonify({"error": "session_id, question_id, user_answer required"}), 400

    try:
        question_id = int(question_id_raw)
    except (TypeError, ValueError):
        return jsonify({"error": "question_id must be an integer"}), 400

    if response_time_ms is not None:
        try:
            response_time_ms = int(response_time_ms)
        except (TypeError, ValueError):
            return jsonify({"error": "response_time_ms must be an integer"}), 400

    session = GameSession.query.get(session_id)
    if not session:
        return jsonify({"error": "Session not found", "session_id": session_id}), 404

    if _is_session_expired(session):
        return jsonify({"error": "Session expired", "session_id": session_id}), 403

    if session.is_completed:
        return jsonify({"error": "Session already completed", "session_id": session_id}), 409

    question = Question.query.get(question_id)
    if not question:
        return jsonify({"error": "Question not found", "question_id": question_id}), 404

    interaction = (
        PlayerInteraction.query
        .filter_by(session_id=session_id, question_id=question_id)
        .order_by(PlayerInteraction.timestamp.desc(), PlayerInteraction.id.desc())
        .first()
    )

    if not interaction:
        return jsonify({"error": "No interaction found for this question in session"}), 400

    is_correct = _normalize(user_answer) == _normalize(question.correct_answer)

    try:
        interaction.user_answer = str(user_answer)
        interaction.is_correct = bool(is_correct)
        interaction.response_time_ms = response_time_ms

        if is_correct:
            session.is_completed = True
            session.end_time = datetime.utcnow()
        else:
            session.attempts_count += 1

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify({
        "is_correct": is_correct,
        "session_completed": session.is_completed,
        "attempts_count": session.attempts_count,
        "message": "Correct! You found the gas holder." if is_correct else "Incorrect. Try again.",
    }), 200
