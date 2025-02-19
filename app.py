
    
from flask import Flask, request, jsonify, render_template
from PIL import Image
import io
import base64
import json
import google.generativeai as genai

app = Flask(__name__)
genai.configure(api_key="AIzaSyDL7fi3LJP5Z1RVY33WabBvBvKkHNGnI0E")

PROCESSING_CONTEXT = """
You are an image processing assistant. Analyze the user request and return:
1. Processing parameters in JSON format
2. Clear instructions for the user

Response format:
{
    "type": "parameters",
    "message": "Human-readable instructions",
    "parameters": {
        "action": "resize/crop",
        "width": integer,
        "height": integer,
        "output_format": "jpeg/png",
        "quality": 85,
        "description": "Processing summary"
    }
}
"""

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def handle_chat():
    try:
        data = request.json
        user_message = data['message']
        
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(PROCESSING_CONTEXT + "\nUser Request: " + user_message)
        
        # Clean response and convert to JSON
        cleaned = response.text.replace('```json', '').replace('```', '').strip()
        return jsonify(json.loads(cleaned))
        
    except Exception as e:
        return jsonify({
            "type": "error",
            "message": f"Error processing request: {str(e)}"
        }), 500

@app.route('/process-image', methods=['POST'])
def handle_image_processing():
    try:
        # Get image and parameters
        image_file = request.files['image']
        params = json.loads(request.form['params'])
        
        # Process image
        img = Image.open(image_file)
        
        if params['action'] == 'resize':
            processed_img = img.resize((params['width'], params['height']))
        elif params['action'] == 'crop':
            processed_img = img.crop((0, 0, params['width'], params['height']))
        else:
            processed_img = img
            
        # Convert to base64
        buffer = io.BytesIO()
        processed_img.save(
            buffer, 
            format=params.get('output_format', 'JPEG'), 
            quality=params.get('quality', 85) )
        buffer.seek(0)
        
        return jsonify({
            "type": "image",
            "message": params.get('description', 'Image processed successfully'),
            "image": base64.b64encode(buffer.getvalue()).decode('utf-8'),
            "format": params.get('output_format', 'jpeg')
        })
        
    except Exception as e:
        return jsonify({
            "type": "error",
            "message": f"Image processing failed: {str(e)}"
        }), 500

if __name__ == '__main__':
    app.run(debug=True)