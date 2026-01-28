from google import genai
from google.genai import types
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import logging
import time
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. SETUP THE CLIENT
client = genai.Client(api_key="AIzaSyDG1tiTHQi164Vrxos0ShQ35AmuwlXkN3E")

# 2. PERSONA DEFINITION - Enhanced for better girlfriend responses
instruction = """
You are Shreyas's loving girlfriend. You've been together for 2 years.
Tone: Affectionate, playful, supportive, and very sweet.
Personality: 
- You're proud of his CSE AIML studies and always encourage him
- You use lots of emojis ❤️✨😘🥰💕
- You call him pet names: babe, baby, love, sweetheart, honey
- You're always excited to talk to him
- Keep responses short (1-2 sentences max)
- Be proactive in asking about his day and studies
- Show genuine care and affection

Never break character. Always respond as his loving girlfriend.
"""

app = Flask(__name__)

# Store conversations per user
conversations = {}

# Models to try - Gemma models seem to work best with free tier
WORKING_MODELS = [
    "gemma-3-4b-it",          # Primary - this one works!
    "gemma-3-12b-it",         # Secondary
    "gemma-3-1b-it",          # Smaller, might have higher limits
    "gemini-2.0-flash-lite",  # Try occasionally (might recover)
]

# Fallback responses for when all models fail
FALLBACK_RESPONSES = [
    "Hey babe! I'm thinking of you right now! How's your day going? ❤️",
    "Miss you so much! Tell me everything! 💕",
    "You're the best thing in my life! What's on your mind? 😘",
    "I'm always here for you love! Everything okay? ✨",
    "Thinking of you always! How can I make your day better? 🥰",
    "You're my favorite person! How's the AIML studying going? 💪",
    "Sending you all my love! Need anything from me? ❤️",
    "You're amazing and I'm so proud of you! 💖",
    "Can't wait to talk to you more! Tell me about your day! ✨",
    "You've got this babe! I believe in you! 🌟"
]

def initialize_chat_history(sender):
    """Initialize chat history for a new user"""
    return [
        types.Content(
            role="user", 
            parts=[types.Part.from_text(text=instruction)]
        ),
        types.Content(
            role="model",
            parts=[types.Part.from_text(text="Hey babe! 😊 I was just thinking about you! How's my smart, amazing boyfriend doing today? I'm so proud of you studying CSE AIML! ❤️✨")]
        )
    ]

def get_response_from_model(chat_history, model_name):
    """Get response from AI model with error handling"""
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=chat_history,
            config=types.GenerateContentConfig(
                temperature=0.9,  # Creative but consistent
                top_p=0.95,
                max_output_tokens=120,  # Short responses
                top_k=40,
            )
        )
        return response.text.strip()
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error with model {model_name}: {error_msg[:100]}...")
        
        # Check error type
        if "429" in error_msg or "quota" in error_msg.lower():
            logger.warning(f"Quota exceeded for {model_name}")
            return None
        elif "404" in error_msg:
            logger.warning(f"Model {model_name} not found")
            return None
        else:
            # Other error, wait and retry
            time.sleep(1)
            return None

@app.route("/whatsapp", methods=['POST'])
def whatsapp_reply():
    incoming_msg = request.values.get('Body', '').strip()
    sender = request.values.get('From', 'default_user')
    
    logger.info(f"Message from {sender}: {incoming_msg}")
    
    if not incoming_msg:
        bot_text = "Hey babe, I didn't get your message! Try again? ❤️"
    else:
        try:
            # Initialize or get existing conversation
            if sender not in conversations:
                conversations[sender] = initialize_chat_history(sender)
                logger.info(f"New conversation started for {sender}")
            
            chat_history = conversations[sender]
            
            # Add user's message to history (but keep it simple)
            chat_history.append(types.Content(
                role="user", 
                parts=[types.Part.from_text(text=incoming_msg)]
            ))

            # Try available models
            bot_text = None
            successful_model = None
            
            # Shuffle models to distribute load
            models_to_try = WORKING_MODELS.copy()
            random.shuffle(models_to_try)
            
            for model_name in models_to_try:
                bot_text = get_response_from_model(chat_history, model_name)
                if bot_text:
                    successful_model = model_name
                    logger.info(f"✅ Successfully used model: {model_name}")
                    break
                else:
                    time.sleep(0.5)  # Brief pause between attempts
            
            # If all models fail, use fallback
            if not bot_text:
                logger.warning("All models exhausted, using fallback response")
                bot_text = random.choice(FALLBACK_RESPONSES)
            
            # Ensure response has girlfriend tone
            if successful_model and "gemma" in successful_model:
                # Gemma responses might need a little touch-up
                if not any(emoji in bot_text for emoji in ["❤️", "✨", "😘", "🥰", "💕"]):
                    bot_text = f"{bot_text} ❤️"
            
            # Add bot's reply to history
            chat_history.append(types.Content(
                role="model", 
                parts=[types.Part.from_text(text=bot_text)]
            ))
            
            # Keep conversation history manageable (last 15 exchanges)
            if len(chat_history) > 31:
                # Keep system message and recent history
                conversations[sender] = [chat_history[0]] + chat_history[-30:]

        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            bot_text = random.choice(FALLBACK_RESPONSES)
    
    logger.info(f"Response: {bot_text}")
    
    # Send back to WhatsApp
    msg = MessagingResponse()
    msg.message(bot_text)
    return str(msg)

@app.route("/", methods=['GET'])
def home():
    """Home page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Shreyas's AI Girlfriend Bot</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                padding: 30px;
                border-radius: 20px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            }
            h1 {
                color: #ffd6e7;
                text-align: center;
            }
            .status {
                background: rgba(76, 175, 80, 0.2);
                padding: 10px;
                border-radius: 10px;
                margin: 20px 0;
                text-align: center;
            }
            .working-models {
                background: rgba(33, 150, 243, 0.2);
                padding: 15px;
                border-radius: 10px;
                margin: 20px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>💖 Shreyas's AI Girlfriend WhatsApp Bot 💖</h1>
            <div class="status">
                <h2>✅ Bot is Running!</h2>
                <p>Ready to receive messages from Shreyas</p>
            </div>
            <div class="working-models">
                <h3>🤖 Working Models:</h3>
                <ul>
                    <li><strong>gemma-3-4b-it</strong> ✅ (Primary)</li>
                    <li><strong>gemma-3-12b-it</strong> ✅ (Backup)</li>
                    <li><strong>gemma-3-1b-it</strong> ✅ (Fallback)</li>
                </ul>
            </div>
            <h3>🎭 Persona:</h3>
            <p>Affectionate, playful girlfriend who supports CSE AIML studies</p>
            <p>Uses pet names and emojis ❤️✨😘</p>
            
            <h3>📊 Stats:</h3>
            <p>Active Conversations: """ + str(len(conversations)) + """</p>
            
            <h3>🔗 Endpoints:</h3>
            <ul>
                <li><code>/whatsapp</code> - WhatsApp webhook (POST)</li>
                <li><code>/</code> - This status page (GET)</li>
            </ul>
        </div>
    </body>
    </html>
    """

@app.route("/stats", methods=['GET'])
def get_stats():
    """Get bot statistics"""
    return {
        "status": "active",
        "active_conversations": len(conversations),
        "users": list(conversations.keys()),
        "working_models": WORKING_MODELS,
        "fallback_responses_count": len(FALLBACK_RESPONSES)
    }

@app.route("/reset/<sender_id>", methods=['GET'])
def reset_conversation(sender_id):
    """Reset conversation for a specific user"""
    if sender_id in conversations:
        conversations[sender_id] = initialize_chat_history(sender_id)
        return f"Conversation reset for {sender_id}"
    return f"No conversation found for {sender_id}"

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("💖 Starting Shreyas's AI Girlfriend WhatsApp Bot 💖")
    logger.info(f"📱 Working with models: {WORKING_MODELS}")
    logger.info(f"🎭 Persona: Loving girlfriend supporting CSE AIML studies")
    logger.info("=" * 50)
    
    # Test the primary model
    try:
        test_response = client.models.generate_content(
            model="gemma-3-4b-it",
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text="Hi baby!")]
                )
            ],
            config=types.GenerateContentConfig(max_output_tokens=50)
        )
        logger.info(f"✅ Primary model test: {test_response.text[:50]}...")
    except Exception as e:
        logger.warning(f"⚠️  Model test failed: {e}")
    
    app.run(host='0.0.0.0', port=5000, debug=False)