import os
import openai

class OpenAIAdapter:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        openai.api_key = self.api_key

    def call_function(self, function_name, params):
        # Example: Only weather for now, expand as needed
        if function_name == 'get_current_weather':
            location = params.get('location', '')
            # This is a stub, replace with OpenAI function call logic
            if 'pardes hanna' in location.lower():
                return {
                    "location": "Pardes Hanna-Karkur, Haifa District, Israel",
                    "temperature_celsius": 28,
                    "condition": "Partly Cloudy",
                    "humidity": 70,
                    "wind_speed_kph": 15
                }
            else:
                return {"error": "Weather data not available for this location via this tool."}
        return {"error": "Function not implemented."}
