import os
import logging
from flask import Flask, render_template, request, jsonify
from wifi_parser import parse_wifi_data
from oui_lookup import lookup_ouis

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        if 'file' not in request.files and not request.form.get('text_input'):
            return jsonify({"error": "No file or text input provided"}), 400
        
        # Get data either from file or direct text input
        if 'file' in request.files and request.files['file'].filename:
            file = request.files['file']
            content = file.read().decode('utf-8')
        else:
            content = request.form.get('text_input', '')
        
        
        if not content.strip():
            return jsonify({"error": "The provided input is empty"}), 400
            
        # Parse the input data
        parsed_data = parse_wifi_data(content)
        
        if not parsed_data:
            return jsonify({"error": "Could not parse any valid WiFi data from the input"}), 400
        
        # Lookup OUIs for each BSSID
        results = lookup_ouis(parsed_data)
        
        # Format the results
        formatted_results = []
        for item in results:
            vendor = item['vendor'] if item['vendor'] else "UNKNOWN VENDOR - POTENTIALLY ROGUE"
            flag = item['vendor'] is None
            
            formatted_results.append({
                'ssid': item['ssid'],
                'bssid': item['bssid'],
                'vendor': item['vendor'],
                'vendor_source': item['vendor_source'],
                'flagged': item['flagged']
            })
        
        return jsonify({
            "results": formatted_results,
            "total": len(formatted_results),
            "flagged": sum(1 for item in formatted_results if item['flagged'])
        })
        
    except Exception as e:
        logger.exception("Error processing WiFi data")
        return jsonify({"error": "An internal server error occurred"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
