from flask import Blueprint, request, jsonify, g
from flask_restful import Api, Resource
from flask_login import current_user, login_required
from datetime import datetime
from api.jwt_authorize import token_required
from __init__ import db
from model.github import GitHubUser, GitHubOrg
from model.user import User
import time

# Gas-game analytics (Phase 4)
from sqlalchemy import func, case
from model.game_session import GameSession
from model.player_interaction import PlayerInteraction
from model.question import Question



analytics_api = Blueprint('analytics_api', __name__, url_prefix='/api/analytics')
api = Api(analytics_api)



def get_date_range(body):
    start_date = body.get('start_date')
    end_date = body.get('end_date')
    
    if not start_date or not end_date:
        today = datetime.today()
        year = today.year

        if datetime(year, 6, 15) <= today <= datetime(year, 11, 14):  # Trimester 1
            start_date = datetime(year, 6, 1)
            end_date = datetime(year, 11, 14)
        elif datetime(year, 11, 15) <= today or today <= datetime(year, 3, 31):  # Trimester 2 (extended to March 31)
            if today.month <= 3:  # If Jan–Mar, adjust to previous year
                year -= 1  
            start_date = datetime(year, 9, 1)
            end_date = datetime(year + 1, 3, 31)  # Now includes all of March
        elif datetime(year, 4, 1) <= today <= datetime(year, 6, 14):  # Trimester 3 (fixed start)
            start_date = datetime(year, 4, 1)
            end_date = datetime(year, 6, 14)
        else:
            raise ValueError(f"Date {today.strftime('%Y-%m-%d')} is out of the defined trimesters")

        start_date = start_date.strftime('%Y-%m-%d')
        end_date = end_date.strftime('%Y-%m-%d')

    return start_date, end_date


@analytics_api.route('/player/<int:user_id>', methods=['GET'])
def gasgame_player_analytics(user_id: int):
    """Phase 4: Player performance history for the gas-game."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found", "user_id": user_id}), 404

    limit = request.args.get('limit', default=25, type=int)
    limit = max(1, min(limit, 200))

    sessions = (
        GameSession.query
        .filter(GameSession.user_id == user_id)
        .order_by(GameSession.start_time.desc())
        .limit(limit)
        .all()
    )

    session_ids = [s.session_id for s in sessions]

    # Aggregate interaction stats by session
    interaction_rows = []
    if session_ids:
        interaction_rows = (
            db.session.query(
                PlayerInteraction.session_id.label('session_id'),
                func.count(PlayerInteraction.id).label('interaction_count'),
                func.sum(case((PlayerInteraction.question_id.isnot(None), 1), else_=0)).label('questions_seen'),
                func.sum(case((PlayerInteraction.is_correct.is_(True), 1), else_=0)).label('correct_count'),
                func.avg(PlayerInteraction.response_time_ms).label('avg_response_time_ms'),
            )
            .filter(PlayerInteraction.session_id.in_(session_ids))
            .group_by(PlayerInteraction.session_id)
            .all()
        )

    by_session = {r.session_id: r for r in interaction_rows}

    # Compute top-level aggregates
    total_sessions = len(sessions)
    completed_sessions = sum(1 for s in sessions if s.is_completed)

    durations_s = []
    for s in sessions:
        if s.is_completed and s.start_time and s.end_time:
            durations_s.append((s.end_time - s.start_time).total_seconds())

    avg_completion_time_s = round(sum(durations_s) / len(durations_s), 2) if durations_s else None
    avg_attempts = round(sum(s.attempts_count for s in sessions) / total_sessions, 2) if total_sessions else 0

    recent_sessions = []
    for s in sessions:
        row = by_session.get(s.session_id)
        duration = None
        if s.is_completed and s.start_time and s.end_time:
            duration = round((s.end_time - s.start_time).total_seconds(), 2)

        recent_sessions.append({
            "session_id": s.session_id,
            "start_time": s.start_time.isoformat() if s.start_time else None,
            "end_time": s.end_time.isoformat() if s.end_time else None,
            "is_completed": s.is_completed,
            "attempts_count": s.attempts_count,
            "duration_s": duration,
            "questions_seen": int(row.questions_seen) if row and row.questions_seen is not None else 0,
            "correct_count": int(row.correct_count) if row and row.correct_count is not None else 0,
            "avg_response_time_ms": round(float(row.avg_response_time_ms), 2) if row and row.avg_response_time_ms is not None else None,
        })

    return jsonify({
        "user": {"id": user.id, "uid": user.uid, "name": user.name},
        "summary": {
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "completion_rate": round(completed_sessions / total_sessions, 4) if total_sessions else 0,
            "avg_completion_time_s": avg_completion_time_s,
            "avg_attempts": avg_attempts,
        },
        "recent_sessions": recent_sessions,
    }), 200


@analytics_api.route('/questions', methods=['GET'])
def gasgame_question_analytics():
    """Phase 4: Question difficulty and success rates."""
    limit = request.args.get('limit', default=50, type=int)
    limit = max(1, min(limit, 500))
    category = request.args.get('category', default=None, type=str)
    difficulty = request.args.get('difficulty_level', default=None, type=int)

    base = (
        db.session.query(
            Question.id.label('question_id'),
            Question.question_text.label('question_text'),
            Question.difficulty_level.label('difficulty_level'),
            Question.category.label('category'),
            Question.college_board_aligned.label('college_board_aligned'),
            func.count(PlayerInteraction.id).label('attempt_count'),
            func.sum(case((PlayerInteraction.is_correct.is_(True), 1), else_=0)).label('correct_count'),
            func.avg(PlayerInteraction.response_time_ms).label('avg_response_time_ms'),
        )
        .outerjoin(PlayerInteraction, PlayerInteraction.question_id == Question.id)
        .group_by(Question.id)
    )

    if category:
        base = base.filter(Question.category == category)
    if difficulty is not None:
        base = base.filter(Question.difficulty_level == difficulty)

    rows = base.order_by(func.count(PlayerInteraction.id).desc(), Question.id.asc()).limit(limit).all()

    results = []
    for r in rows:
        attempt_count = int(r.attempt_count or 0)
        correct_count = int(r.correct_count or 0)
        results.append({
            "question_id": r.question_id,
            "question_text": r.question_text,
            "difficulty_level": r.difficulty_level,
            "category": r.category,
            "college_board_aligned": bool(r.college_board_aligned),
            "attempt_count": attempt_count,
            "correct_count": correct_count,
            "correct_rate": round(correct_count / attempt_count, 4) if attempt_count else None,
            "avg_response_time_ms": round(float(r.avg_response_time_ms), 2) if r.avg_response_time_ms is not None else None,
        })

    return jsonify({
        "count": len(results),
        "results": results,
    }), 200


@analytics_api.route('/sessions', methods=['GET'])
def gasgame_session_analytics():
    """Phase 4: Session analytics (completion time, retry rates)."""
    limit = request.args.get('limit', default=500, type=int)
    limit = max(1, min(limit, 5000))

    sessions = (
        GameSession.query
        .order_by(GameSession.start_time.desc())
        .limit(limit)
        .all()
    )

    total_sessions = len(sessions)
    completed = [s for s in sessions if s.is_completed and s.start_time and s.end_time]
    completed_sessions = len(completed)

    durations = [(s.end_time - s.start_time).total_seconds() for s in completed]
    avg_completion_time_s = round(sum(durations) / len(durations), 2) if durations else None

    retry_sessions = sum(1 for s in sessions if (s.attempts_count or 0) > 0)

    return jsonify({
        "summary": {
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "completion_rate": round(completed_sessions / total_sessions, 4) if total_sessions else 0,
            "avg_completion_time_s": avg_completion_time_s,
            "avg_attempts": round(sum((s.attempts_count or 0) for s in sessions) / total_sessions, 2) if total_sessions else 0,
            "retry_rate": round(retry_sessions / total_sessions, 4) if total_sessions else 0,
        }
    }), 200



class GitHubUserAPI(Resource):
    @token_required()
    def get(self):
        try:
            current_user = g.current_user
            github_user_resource = GitHubUser()
            response = github_user_resource.get(current_user.uid)
            
            if response[1] != 200:
                return response

            return jsonify(response[0])
        except Exception as e:
            return {'message': str(e)}, 500

class UserProfileLinks(Resource):
    @token_required()
    def get(self):
        try:
            current_user = g.current_user
            github_user_resource = GitHubUser()
            response = github_user_resource.get_profile_links(current_user.uid)
            
            if response[1] != 200:
                return response

            return jsonify(response[0])
        except Exception as e:
            return {'message': str(e)}, 500

class UserCommits(Resource):
    @token_required()
    def get(self):
        try:
            current_user = g.current_user
            try:
                body = request.get_json()
            except Exception as e:
                body = {}
            
            start_date, end_date = get_date_range(body)

            github_user_resource = GitHubUser()
            response = github_user_resource.get_commit_stats(current_user.uid, start_date, end_date)
            
            if response[1] != 200:
                return response

            return jsonify(response[0])
        except Exception as e:
            return {'message': str(e)}, 500
class UserPrs(Resource):
    @token_required()
    def get(self):
        try:
            current_user = g.current_user
            try:
                body = request.get_json()
            except Exception as e:
                body = {}
            
            start_date, end_date = get_date_range(body)

            github_user_resource = GitHubUser()
            response = github_user_resource.get_pr_stats(current_user.uid, start_date, end_date)
            
            if response[1] != 200:
                return response

            return jsonify(response[0])
        except Exception as e:
            return {'message': str(e)}, 500

class UserIssues(Resource):
    @token_required()
    def get(self):
        try:
            current_user = g.current_user
            try:
                body = request.get_json()
            except Exception as e:
                body = {}
            
            start_date, end_date = get_date_range(body)

            github_user_resource = GitHubUser()
            response = github_user_resource.get_issue_stats(current_user.uid, start_date, end_date)
            
            if response[1] != 200:
                return response

            return jsonify(response[0])
        except Exception as e:
            return {'message': str(e)}, 500

class UserIssueComments(Resource):
    @token_required()
    def get(self):
        try:
            current_user = g.current_user
            try:
                body = request.get_json()
            except Exception as e:
                body = {}
            
            start_date, end_date = get_date_range(body)

            github_user_resource = GitHubUser()
            response = github_user_resource.get_issue_comment_stats(current_user.uid, start_date, end_date)
            
            if response[1] != 200:
                return response

            return jsonify(response[0])
        except Exception as e:
            return {'message': str(e)}, 500

class UserReceivedIssueComments(Resource):
    def get(self):
        try:
            current_user = g.current_user
            try:
                body = request.get_json()
            except Exception as e:
                body = {}
            
            start_date, end_date = get_date_range(body)

            github_user_resource = GitHubUser()
            response = github_user_resource.get_total_received_issue_comments(current_user.uid, start_date, end_date)
            
            if response[1] != 200:
                return response

            return jsonify(response[0])
        except Exception as e:
            return {'message': str(e)}, 500

class GitHubOrgUsers(Resource):
    def get(self, org_name):
        try:
            github_org_resource = GitHubOrg()
            response = github_org_resource.get_users(org_name)
            
            if response[1] != 200:
                return response

            return jsonify(response[0])
        except Exception as e:
            return {'message': str(e)}, 500

class GitHubOrgRepos(Resource):
    def get(self, org_name):
        try:
            github_org_resource = GitHubOrg()
            response = github_org_resource.get_repos(org_name)
            
            if response[1] != 200:
                return response

            return jsonify(response[0])
        except Exception as e:
            return {'message': str(e)}, 500
        
class AdminUserIssues(Resource):
    @token_required()
    def get(self, uid):
        try:
            # Check if the current user is an Admin
            if g.current_user.role != 'Admin':
                return {'message': 'Access denied: Admins only.'}, 403

            # Fetch the request body to extract date range (if any)
            try:
                body = request.get_json()
            except Exception as e:
                body = {}

            # Determine date range from body or use default trimester logic
            start_date, end_date = get_date_range(body)

            # Fetch the user based on uid
            user = User.query.filter_by(_uid=uid).first()
            if not user:
                return {'message': 'User not found'}, 404

            # Fetch submitted issue data for the specific user
            github_user_resource = GitHubUser()
            response = github_user_resource.get_issue_stats(user.uid, start_date, end_date)

            # Check if response is None or doesn't have the expected structure
            if response is None or len(response) < 2:
                return {'message': 'Error fetching issues for this user'}, 500

            # Return the user's UID and issue stats
            return jsonify({
                'uid': user.uid,
                'issues': response[0]
            })

        except Exception as e:
            return {'message': str(e)}, 500


class AdminUserCommits(Resource):
    @token_required()
    def get(self, uid):
        try:
            # Check if the current user has 'Admin' role; if not, deny access with a 403 status
            if g.current_user.role != 'Admin':
                return {'message': 'Access denied: Admins only.'}, 403

            # Attempt to parse the request's JSON body; if the request does not contain valid JSON, assign an empty dictionary
            try:
                body = request.get_json()
            except Exception as e:
                body = {}

            # Extract the start and end date from the parsed body; fallback to default values if not provided
            start_date, end_date = get_date_range(body)

            # Query the database to find the user by the provided unique user ID (uid)
            user = User.query.filter_by(_uid=uid).first()

            # If the user is not found, return a 404 Not Found error message
            if not user:
                return {'message': 'User not found'}, 404

            github_user_resource = GitHubUser()
            
            # Retrieve the commit statistics for the given user, filtered by the date range
            response = github_user_resource.get_commit_stats(user.uid, start_date, end_date)
            
            if response is None or len(response) < 2:
                return {'message': 'Error fetching commits for this user'}, 500

            return jsonify({
                'uid': user.uid,
                'commits': response[0]  # Assuming the first item in response contains the commit data
            })

        except Exception as e:
            return {'message': str(e)}, 500

    def check_rate_limit(self, response):
        """Check if the rate limit is exceeded based on response headers"""
        remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
        reset_time = int(response.headers.get('X-RateLimit-Reset', time.time()))
        if remaining == 0:
            # If no requests remaining, calculate the time to wait
            wait_time = reset_time - time.time()
            print(f"Rate limit exceeded. Waiting for {wait_time} seconds.")
            time.sleep(wait_time + 5)  # Adding a buffer time to avoid immediate retry
            return True
        return False

    def retry_request(self, user_uid, start_date, end_date, retries=3):
        """Retry the request in case of rate limiting or server error"""
        attempt = 0
        while attempt < retries:
            try:
                github_user_resource = GitHubUser()
                response = github_user_resource.get_commit_stats(user_uid, start_date, end_date)

                if response.status_code == 500:
                    print(f"Attempt {attempt + 1}: Server error, retrying...")
                    time.sleep(5 * (2 ** attempt))  # Exponential backoff
                elif response.status_code == 403:
                    if self.check_rate_limit(response):
                        return self.retry_request(user_uid, start_date, end_date)
                else:
                    return response.json()  # Successfully processed the request
            except Exception as e:
                print(f"Error occurred: {e}")
            attempt += 1
        return None  # If retries are exhausted


api.add_resource(GitHubUserAPI, '/github/user')
api.add_resource(UserProfileLinks, '/github/user/profile_links')
api.add_resource(UserCommits, '/github/user/commits')
api.add_resource(UserPrs, '/github/user/prs')
api.add_resource(UserIssues, '/github/user/issues')
api.add_resource(UserIssueComments, '/github/user/issue_comments')
api.add_resource(UserReceivedIssueComments, '/github/user/received_issue_comments')
api.add_resource(GitHubOrgUsers, '/github/org/<string:org_name>/users')
api.add_resource(GitHubOrgRepos, '/github/org/<string:org_name>/repos')
api.add_resource(AdminUserCommits, '/commits/<string:uid>')  # Admin endpoint for commits
api.add_resource(AdminUserIssues, '/issues/<string:uid>')  # Admin endpoint for issues