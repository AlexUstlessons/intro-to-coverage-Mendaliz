from flask import Blueprint, request, jsonify
from app.services import user_service

users_bp = Blueprint('users', __name__)


@users_bp.route('/', methods=['POST'])
def create_user():
    data = request.get_json()
    user = user_service.create_user(data['name'], data['email'])
    return jsonify(user.to_dict()), 201


@users_bp.route('/', methods=['GET'])
def list_users():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    result = user_service.get_all_users(page, per_page)
    return jsonify({
        'items': [u.to_dict() for u in result['items']],
        'total': result['total'],
        'page': result['page'],
        'pages': result['pages'],
    })


@users_bp.route('/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = user_service.get_user(user_id)
    return jsonify(user.to_dict())


@users_bp.route('/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    data = request.get_json()
    user = user_service.update_user(
        user_id,
        name=data.get('name'),
        email=data.get('email'),
    )
    return jsonify(user.to_dict())


@users_bp.route('/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user_service.delete_user(user_id)
    return jsonify({'message': 'User deleted'}), 200


@users_bp.route('/<int:user_id>/verify-email', methods=['POST'])
def verify_email(user_id):
    user = user_service.verify_email(user_id)
    return jsonify(user.to_dict())


@users_bp.route('/search', methods=['GET'])
def search_users():
    q = request.args.get('q', '')
    users = user_service.search_users(q)
    return jsonify([u.to_dict() for u in users])


@users_bp.route('/<int:user_id>/summary', methods=['GET'])
def get_user_summary(user_id):
    summary = user_service.get_user_summary(user_id)
    return jsonify(summary)
