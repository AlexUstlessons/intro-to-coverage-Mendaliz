from flask import Blueprint, request, jsonify
from app.services import loan_service

loans_bp = Blueprint('loans', __name__)


@loans_bp.route('/', methods=['POST'])
def apply_for_loan():
    data = request.get_json()
    loan = loan_service.apply_for_loan(
        data['user_id'],
        data['amount'],
        data['interest_rate'],
        data['term_months'],
    )
    return jsonify(loan.to_dict()), 201


@loans_bp.route('/<int:loan_id>', methods=['GET'])
def get_loan(loan_id):
    loan = loan_service.get_loan(loan_id)
    return jsonify(loan.to_dict())


@loans_bp.route('/user/<int:user_id>', methods=['GET'])
def get_user_loans(user_id):
    loans = loan_service.get_user_loans(user_id)
    return jsonify([loan.to_dict() for loan in loans])


@loans_bp.route('/<int:loan_id>/approve', methods=['POST'])
def approve_loan(loan_id):
    loan = loan_service.approve_loan(loan_id)
    return jsonify(loan.to_dict())


@loans_bp.route('/<int:loan_id>/reject', methods=['POST'])
def reject_loan(loan_id):
    loan = loan_service.reject_loan(loan_id)
    return jsonify(loan.to_dict())


@loans_bp.route('/<int:loan_id>/payment', methods=['POST'])
def make_payment(loan_id):
    data = request.get_json()
    loan = loan_service.make_payment(loan_id, data['account_id'])
    return jsonify(loan.to_dict())


@loans_bp.route('/<int:loan_id>/schedule', methods=['GET'])
def get_payment_schedule(loan_id):
    schedule = loan_service.get_payment_schedule(loan_id)
    return jsonify(schedule)


@loans_bp.route('/<int:loan_id>/early-repayment', methods=['POST'])
def early_repayment(loan_id):
    data = request.get_json()
    loan = loan_service.early_repayment(loan_id, data['account_id'])
    return jsonify(loan.to_dict())


@loans_bp.route('/overdue', methods=['GET'])
def get_overdue_loans():
    loans = loan_service.get_overdue_loans()
    return jsonify([loan.to_dict() for loan in loans])
