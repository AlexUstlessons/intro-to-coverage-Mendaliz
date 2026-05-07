from flask import Blueprint, request, jsonify
from app.services import account_service
from app.utils import parse_date_range

accounts_bp = Blueprint('accounts', __name__)


@accounts_bp.route('/', methods=['POST'])
def create_account():
    data = request.get_json()
    account = account_service.create_account(data['user_id'], data['type'])
    return jsonify(account.to_dict()), 201


@accounts_bp.route('/user/<int:user_id>', methods=['GET'])
def get_user_accounts(user_id):
    accounts = account_service.get_user_accounts(user_id)
    return jsonify([a.to_dict() for a in accounts])


@accounts_bp.route('/<int:account_id>', methods=['GET'])
def get_account(account_id):
    account = account_service.get_account(account_id)
    return jsonify(account.to_dict())


@accounts_bp.route('/<int:account_id>/deposit', methods=['POST'])
def deposit(account_id):
    data = request.get_json()
    account = account_service.deposit(account_id, data['amount'])
    return jsonify(account.to_dict())


@accounts_bp.route('/<int:account_id>/withdraw', methods=['POST'])
def withdraw(account_id):
    data = request.get_json()
    account = account_service.withdraw(account_id, data['amount'])
    return jsonify(account.to_dict())


@accounts_bp.route('/<int:account_id>/freeze', methods=['POST'])
def freeze_account(account_id):
    account = account_service.freeze_account(account_id)
    return jsonify(account.to_dict())


@accounts_bp.route('/<int:account_id>/unfreeze', methods=['POST'])
def unfreeze_account(account_id):
    account = account_service.unfreeze_account(account_id)
    return jsonify(account.to_dict())


@accounts_bp.route('/<int:account_id>/close', methods=['POST'])
def close_account(account_id):
    account = account_service.close_account(account_id)
    return jsonify(account.to_dict())


@accounts_bp.route('/<int:account_id>/overdraft', methods=['POST'])
def set_overdraft(account_id):
    data = request.get_json()
    account = account_service.set_overdraft(account_id, data['enabled'])
    return jsonify(account.to_dict())


@accounts_bp.route('/<int:account_id>/history', methods=['GET'])
def get_balance_history(account_id):
    txs = account_service.get_balance_history(account_id)
    return jsonify([tx.to_dict() for tx in txs])


@accounts_bp.route('/<int:account_id>/statement', methods=['GET'])
def get_statement(account_id):
    from_str = request.args.get('from')
    to_str = request.args.get('to')
    from_date, to_date = parse_date_range(from_str, to_str)
    txs = account_service.get_statement(account_id, from_date, to_date)
    return jsonify([tx.to_dict() for tx in txs])


@accounts_bp.route('/bulk-deposit', methods=['POST'])
def bulk_deposit():
    data = request.get_json()
    accounts = account_service.bulk_deposit(data['deposits'])
    return jsonify([a.to_dict() for a in accounts])
