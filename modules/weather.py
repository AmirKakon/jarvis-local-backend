from flask import Blueprint, request, jsonify

def register(app, mcp_adapter):
    weather_bp = Blueprint('weather', __name__)

    @weather_bp.route('/api/weather', methods=['GET'])
    def get_weather():
        location = request.args.get('location', 'Pardes Hanna-Karkur')
        result = mcp_adapter.call_function('get_current_weather', {'location': location})
        return jsonify(result)

    app.register_blueprint(weather_bp)
