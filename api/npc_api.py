from flask import Blueprint, request, jsonify
from sqlalchemy import func

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

    # Choose question only if this NPC is the gas holder for this session.
    if is_gas_holder:
        used_question_ids_subq = (
            db.session.query(PlayerInteraction.question_id)
            .filter(
                PlayerInteraction.session_id == session_id,
                PlayerInteraction.question_id.isnot(None),
            )
            .subquery()
        )

        question = (
            Question.query
            .filter(Question.correct_answer.isnot(None))
            .filter(Question.options.isnot(None))
            .filter(~Question.id.in_(used_question_ids_subq))
            .order_by(func.random())
            .first()
        )

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
            "npc": {**npc.to_public_dict(), "is_gas_holder": True},
            "question": question.to_public_dict() if question else None,
            "message": None if question else "No questions available",
        }), 200

    interaction = PlayerInteraction(
        session_id=session_id,
        npc_id=npc.id,
        question_id=None,
    )
    try:
        db.session.add(interaction)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return jsonify({
        "result": "success",
        "npc": {**npc.to_public_dict(), "is_gas_holder": False},
        "message": "NPC interaction successful",
    }), 200
