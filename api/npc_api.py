from flask import Blueprint, request, jsonify
from sqlalchemy import func, select

from __init__ import db
from model.npc import Npc
from model.game_session import GameSession
from model.question import Question
from model.player_interaction import PlayerInteraction


npc_api = Blueprint('npc_api', __name__, url_prefix='/api/npc')


@npc_api.route('/interact', methods=['POST'])
def interact():
    data = request.get_json(silent=True) or {}

    session_id = data.get('session_id')
    npc_id_raw = data.get('npc_id')

    if not session_id or npc_id_raw is None:
        return jsonify({"error": "session_id and npc_id required"}), 400

    try:
        npc_id = int(npc_id_raw)
    except (TypeError, ValueError):
        return jsonify({"error": "npc_id must be an integer"}), 400

    npc = Npc.query.get(npc_id)
    if not npc:
        return jsonify({"error": "NPC not found", "npc_id": npc_id}), 404

    session = GameSession.query.get(session_id)
    if not session:
        return jsonify({"error": "Session not found", "session_id": session_id}), 404

    if session.is_completed:
        return jsonify({"error": "Session already completed", "session_id": session_id}), 409

    is_gas_holder = session.gas_holder_npc_id == npc.id

    # This minigame expects a question for every NPC interaction.
    # We return a question for both gas-holder and non-gas-holder NPCs.
    # Correctness is validated in /api/quiz/answer by checking whether the
    # interaction's npc_id matches the session's gas-holder npc.
    used_question_ids_select = (
        select(PlayerInteraction.question_id)
        .where(
            PlayerInteraction.session_id == session_id,
            PlayerInteraction.question_id.isnot(None),
        )
    )

    question = (
        Question.query
        .filter(Question.correct_answer.isnot(None))
        .filter(Question.options.isnot(None))
        .filter(~Question.id.in_(used_question_ids_select))
        .order_by(func.random())
        .first()
    )

    # If the session has exhausted the question pool, clone a random valid question
    # to guarantee a unique question_id for this interaction.
    if question is None:
        template_question = (
            Question.query
            .filter(Question.correct_answer.isnot(None))
            .filter(Question.options.isnot(None))
            .order_by(func.random())
            .first()
        )

        if template_question is not None:
            question = Question(
                question_text=template_question.question_text,
                correct_answer=template_question.correct_answer,
                options=list(template_question.options) if isinstance(template_question.options, list) else template_question.options,
                difficulty_level=template_question.difficulty_level,
                category=template_question.category,
                college_board_aligned=template_question.college_board_aligned,
            )
        else:
            question = Question(
                question_text='What is 2 + 2?',
                correct_answer='4',
                options=['3', '4', '5', '22'],
                difficulty_level=1,
                category='Default',
                college_board_aligned=False,
            )

        db.session.add(question)
        db.session.flush()  # ensures question.id is available before creating interaction

    interaction = PlayerInteraction(
        session_id=session_id,
        npc_id=npc.id,
        question_id=question.id if question else None,
    )
    try:
        db.session.add(interaction)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify({
        "result": "question",
        "npc": {**npc.to_public_dict(), "is_gas_holder": is_gas_holder},
        "question": question.to_public_dict() if question else None,
        "message": None if question else "No questions available",
    }), 200
