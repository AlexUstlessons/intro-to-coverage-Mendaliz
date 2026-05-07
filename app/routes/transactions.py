from flask import Blueprint, request, jsonify
from app.services import transaction_service
from app.utils import parse_date_range
import datetime

transactions_bp = Blueprint('transactions', __name__)


@transactions_bp.route('/transfer', methods=['POST'])
def transfer():
    data = request.get_json()
    tx = transaction_service.transfer(
        data['from_account_id'],
        data['to_account_id'],
        data['amount'],
        data.get('description'),
    )
    return jsonify(tx.to_dict()), 201


@transactions_bp.route('/deposit', methods=['POST'])
def deposit():
    data = request.get_json()
    tx = transaction_service.create_deposit(
        data['account_id'], data['amount'], data.get('description')
    )
    return jsonify(tx.to_dict()), 201


@transactions_bp.route('/withdraw', methods=['POST'])
def withdraw():
    data = request.get_json()
    tx = transaction_service.create_withdrawal(
        data['account_id'], data['amount'], data.get('description')
    )
    return jsonify(tx.to_dict()), 201


@transactions_bp.route('/<int:tx_id>', methods=['GET'])
def get_transaction(tx_id):
    tx = transaction_service.get_transaction(tx_id)
    return jsonify(tx.to_dict())


@transactions_bp.route('/account/<int:account_id>', methods=['GET'])
def get_account_transactions(account_id):
    type_filter = request.args.get('type')
    from_str = request.args.get('from')
    to_str = request.args.get('to')
    from_date, to_date = parse_date_range(from_str, to_str)
    txs = transaction_service.get_account_transactions(account_id, type_filter, from_date, to_date)
    return jsonify([tx.to_dict() for tx in txs])


@transactions_bp.route('/<int:tx_id>/cancel', methods=['POST'])
def cancel_transaction(tx_id):
    tx = transaction_service.cancel_transaction(tx_id)
    return jsonify(tx.to_dict())


@transactions_bp.route('/batch-transfer', methods=['POST'])
def batch_transfer():
    data = request.get_json()
    txs = transaction_service.batch_transfer(data['from_account_id'], data['recipients'])
    return jsonify([tx.to_dict() for tx in txs]), 201


@transactions_bp.route('/stats/daily', methods=['GET'])
def daily_stats():
    date_str = request.args.get('date', datetime.date.today().isoformat())
    target_date = datetime.date.fromisoformat(date_str)
    return jsonify(transaction_service.get_daily_stats(target_date))


@transactions_bp.route('/stats/monthly', methods=['GET'])
def monthly_stats():
    year = request.args.get('year', datetime.date.today().year, type=int)
    month = request.args.get('month', datetime.date.today().month, type=int)
    return jsonify(transaction_service.get_monthly_stats(year, month))
