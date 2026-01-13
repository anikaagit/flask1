from datetime import datetime, timedelta
from uuid import uuid4

from flask import Blueprint, request, jsonify
from flask_login import current_user
from sqlalchemy import func

from __init__ import db
from model.npc import Npc
from model.game_session import GameSession
from model.player_interaction import PlayerInteraction


game_api = Blueprint('game_api', __name__, url_prefix='/api/game')

SESSION_TIMEOUT_MINUTES = 30


def _is_session_expired(session: GameSession) -> bool:
    if not session or session.is_completed:
        return False
    if not session.start_time:
        return False
    return datetime.utcnow() - session.start_time > timedelta(minutes=SESSION_TIMEOUT_MINUTES)


@game_api.route('/start', methods=['POST'])
def start_game():
    data = request.get_json(silent=True) or {}

    # Prefer logged-in user id; otherwise allow optional user_id in body
    user_id = current_user.id if getattr(current_user, 'is_authenticated', False) else data.get('user_id')

    # Prevent duplicate active sessions for a user
    if user_id:
        active = GameSession.query.filter_by(user_id=user_id, is_completed=False).order_by(GameSession.start_time.desc()).first()
        if active and not _is_session_expired(active):
            npcs = Npc.query.order_by(Npc.id.asc()).all()
            return jsonify({
                "session_id": active.session_id,
                "npcs": [n.to_public_dict() for n in npcs],
                "message": "Resuming active session",
            }), 200

    # Need at least 1 NPC to start
    npc = Npc.query.order_by(func.random()).first()
    if not npc:
        return jsonify({"error": "No NPCs available"}), 400

    # Pick a gas holder NPC randomly
    gas_holder = npc

    session_id = uuid4().hex
    session = GameSession(session_id=session_id, gas_holder_npc_id=gas_holder.id, user_id=user_id)

    try:
        db.session.add(session)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    npcs = Npc.query.order_by(Npc.id.asc()).all()

    return jsonify({
        "session_id": session_id,
        "npcs": [n.to_public_dict() for n in npcs],
        "start_time": session.start_time.isoformat() if session.start_time else None,
    }), 201


@game_api.route('/session/<string:session_id>', methods=['GET'])
def get_session(session_id: str):
    session = GameSession.query.get(session_id)
    if not session:
        return jsonify({"error": "Session not found", "session_id": session_id}), 404

    if _is_session_expired(session):
        return jsonify({"error": "Session expired", "session_id": session_id}), 403

    interactions = (
        PlayerInteraction.query
        .filter_by(session_id=session_id)
        .order_by(PlayerInteraction.timestamp.asc(), PlayerInteraction.id.asc())
        .all()
    )

    interacted_npc_ids = sorted({i.npc_id for i in interactions})
    answered = [i.to_dict() for i in interactions if i.question_id is not None]

    return jsonify({
        "session": session.to_dict(),
        "interacted_npc_ids": interacted_npc_ids,
        "answered_questions": answered,
    }), 200
