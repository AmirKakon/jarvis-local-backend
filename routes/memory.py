from flask import Blueprint, request, jsonify
from services.memory_service import add_memory, get_memory, list_memories, update_memory, delete_memory

memory_bp = Blueprint('memory', __name__)

@memory_bp.route('/api/memory', methods=['POST'])
def create_memory():
    data = request.json
    content = data.get('content')
    type_ = data.get('type', 'note')
    tags = data.get('tags', [])
    memory = add_memory(content, type_, tags)
    return jsonify(memory)

@memory_bp.route('/api/memory/<memory_id>', methods=['GET'])
def read_memory(memory_id):
    memory = get_memory(memory_id)
    if memory:
        return jsonify(memory)
    return jsonify({"error": "Not found"}), 404

@memory_bp.route('/api/memory', methods=['GET'])
def list_memory():
    type_ = request.args.get('type')
    memories = list_memories(type_)
    return jsonify(memories)

@memory_bp.route('/api/memory/<memory_id>', methods=['PUT'])
def update_memory_endpoint(memory_id):
    data = request.json
    content = data.get('content')
    type_ = data.get('type')
    tags = data.get('tags')
    memory = update_memory(memory_id, content, type_, tags)
    return jsonify(memory)

@memory_bp.route('/api/memory/<memory_id>', methods=['DELETE'])
def delete_memory_endpoint(memory_id):
    delete_memory(memory_id)
    return jsonify({"status": "deleted"})
