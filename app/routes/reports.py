from flask import Blueprint, request, jsonify
from app.services import report_service

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/balance/<int:user_id>', methods=['GET'])
def get_user_balance(user_id):
    return jsonify(report_service.get_user_balance(user_id))


@reports_bp.route('/transactions/summary', methods=['GET'])
def get_transaction_summary():
    return jsonify(report_service.get_transaction_summary())


@reports_bp.route('/top-accounts', methods=['GET'])
def get_top_accounts():
    limit = request.args.get('limit', 10, type=int)
    return jsonify(report_service.get_top_accounts(limit))


@reports_bp.route('/revenue', methods=['GET'])
def get_revenue():
    return jsonify(report_service.get_revenue())


@reports_bp.route('/monthly/<int:user_id>', methods=['GET'])
def get_monthly_report(user_id):
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    return jsonify(report_service.get_monthly_report(user_id, month, year))


@reports_bp.route('/risk', methods=['GET'])
def get_risk_analysis():
    return jsonify(report_service.get_risk_analysis())


@reports_bp.route('/audit', methods=['GET'])
def get_audit_log():
    user_id = request.args.get('user_id', type=int)
    action = request.args.get('action')
    return jsonify([log.to_dict() for log in report_service.get_audit_log(user_id, action)])


@reports_bp.route('/daily-volumes', methods=['GET'])
def get_daily_volumes():
    from_str = request.args.get('from')
    to_str = request.args.get('to')
    return jsonify(report_service.get_daily_volumes(from_str, to_str))
