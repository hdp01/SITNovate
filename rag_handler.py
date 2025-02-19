import google.generativeai as genai
import json

genai.configure(api_key="AIzaSyDL7fi3LJP5Z1RVY33WabBvBvKkHNGnI0E")

PROCESSING_CONTEXT = """
You are an expert image processing assistant. Help users by:
1. Asking clarifying questions if requirements are unclear
2. Providing dimension suggestions for common use cases
3. Generating parameters in JSON format when ready

Response format:
{
    "type": "question|parameters|error",
    "message": "Natural language response",
    "parameters": {
        "action": "resize/crop",
        "width": number,
        "height": number,
        "output_format": "jpeg/png",
        "quality": 85,
        "description": "Processing summary"
    }
}
"""

def get_processing_parameters(user_input, conversation_history):
    model = genai.GenerativeModel('gemini-pro')
    chat = model.start_chat(history=conversation_history)
    
    prompt = f"""
    {PROCESSING_CONTEXT}
    
    Conversation History:
    {json.dumps(conversation_history[-3:])}
    
    User Input: {user_input}
    
    Respond with valid JSON only.
    """
    
    try:
        response = chat.send_message(prompt)
        cleaned_response = response.text.replace('```json', '').replace('```', '')
        return json.loads(cleaned_response)
    
    except json.JSONDecodeError:
        return {
            "type": "error",
            "message": "Couldn't understand the request. Please try again."
        }