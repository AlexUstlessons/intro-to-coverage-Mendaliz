from flask import Blueprint, request, jsonify
from app.services import card_service

cards_bp = Blueprint('cards', __name__)


@cards_bp.route('/', methods=['POST'])
def issue_card():
    data = request.get_json()
    card = card_service.issue_card(
        data['account_id'],
        data.get('daily_limit', 1000.0),
    )
    return jsonify(card.to_dict()), 201


@cards_bp.route('/<int:card_id>', methods=['GET'])
def get_card(card_id):
    card = card_service.get_card(card_id)
    return jsonify(card.to_dict())


@cards_bp.route('/account/<int:account_id>', methods=['GET'])
def get_account_cards(account_id):
    cards = card_service.get_account_cards(account_id)
    return jsonify([c.to_dict() for c in cards])


@cards_bp.route('/<int:card_id>/activate', methods=['POST'])
def activate_card(card_id):
    card = card_service.activate_card(card_id)
    return jsonify(card.to_dict())


@cards_bp.route('/<int:card_id>/deactivate', methods=['POST'])
def deactivate_card(card_id):
    card = card_service.deactivate_card(card_id)
    return jsonify(card.to_dict())


@cards_bp.route('/<int:card_id>/limit', methods=['POST'])
def set_daily_limit(card_id):
    data = request.get_json()
    card = card_service.set_daily_limit(card_id, data['limit'])
    return jsonify(card.to_dict())


@cards_bp.route('/<int:card_id>/charge', methods=['POST'])
def charge_card(card_id):
    data = request.get_json()
    card = card_service.charge_card(card_id, data['amount'])
    return jsonify(card.to_dict())


@cards_bp.route('/<int:card_id>/report-stolen', methods=['POST'])
def report_stolen(card_id):
    card = card_service.report_stolen(card_id)
    return jsonify(card.to_dict())


@cards_bp.route('/<int:card_id>/renew', methods=['POST'])
def renew_card(card_id):
    card = card_service.renew_card(card_id)
    return jsonify(card.to_dict())
