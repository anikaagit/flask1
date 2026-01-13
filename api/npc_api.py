from flask import Blueprint, request, jsonify
from sqlalchemy import func

from __init__ import db
from model.npc import Npc, QuestionPool, NpcInteraction


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

    # Choose question only if this NPC is a gas holder.
    if npc.is_gas_holder:
        # Prefer NPC-specific questions; fall back to global ones.
        question = (
            QuestionPool.query
            .filter((QuestionPool.npc_id == npc.id) | (QuestionPool.npc_id.is_(None)))
            .order_by(func.random())
            .first()
        )

        interaction = NpcInteraction(
            session_id=session_id,
            npc_id=npc.id,
            was_gas_holder=True,
            interaction_type='question',
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
            "npc": npc.to_dict(),
            "question": question.to_dict() if question else None,
            "message": None if question else "No questions available",
        }), 200

    interaction = NpcInteraction(
        session_id=session_id,
        npc_id=npc.id,
        was_gas_holder=False,
        interaction_type='success',
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
        "npc": npc.to_dict(),
        "message": "NPC interaction successful",
    }), 200
