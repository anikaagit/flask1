from datetime import datetime

from flask import Blueprint, jsonify
from sqlalchemy import text

from __init__ import db


health_api = Blueprint('health_api', __name__, url_prefix='/api')


@health_api.route('/health', methods=['GET'])
def health():
    """Lightweight health check for dev and deployment sanity checks."""
    db_ok = True
    db_error = None

    try:
        db.session.execute(text('SELECT 1'))
    except Exception as exc:  # pragma: no cover
        db_ok = False
        db_error = str(exc)

    payload = {
        'status': 'ok' if db_ok else 'degraded',
        'time_utc': datetime.utcnow().isoformat() + 'Z',
        'db': 'ok' if db_ok else 'error',
    }

    if db_error:
        payload['db_error'] = db_error

    return jsonify(payload), (200 if db_ok else 503)
