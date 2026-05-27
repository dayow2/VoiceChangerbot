import os
import io
import requests
from flask import Flask, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes
)
from pydub import AudioSegment
import effects
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# === CONFIGURATION ===
TOKEN = os.environ.get("TELEGRAM_TOKEN")
VOICEMOD_API_KEY = os.environ.get("VOICEMOD_API_KEY")
PORT = int(os.environ.get("PORT", 5000))

# === FLASK APP for Render Health Checks ===
flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health_check():
    return jsonify({"status": "ok", "service": "Voice Changer Bot"}), 200

# === VOICE PROCESSING FUNCTIONS ===
def download_voice_file(file_id):
    """Download voice message from Telegram"""
    url = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}"
    response = requests.get(url).json()
    
    if not response.get('ok'):
        return None
    
    file_path = response['result']['file_path']
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    
    audio_response = requests.get(file_url)
    return io.BytesIO(audio_response.content)

def convert_audio_format(audio_bytes, target_format='ogg'):
    """Convert audio between formats using pydub"""
    try:
        # Load audio from bytes
        audio = AudioSegment.from_ogg(io.BytesIO(audio_bytes))
        
        # Export to target format
        output = io.BytesIO()
        audio.export(output, format=target_format)
        output.seek(0)
        return output
    except Exception as e:
        print(f"Audio conversion error: {e}")
        return None

def apply_voice_effect(audio_bytes, effect_name):
    """Apply voice effect using Voicemod API [citation:9]"""
    
    # Map effect names to Voicemod API names
    effect_api_name = effects.get_effect(effect_name)
    if effect_api_name:
        effect_api_name = effect_api_name['api_name']
    else:
        effect_api_name = effect_name
    
    # Voicemod API endpoint
    url = "https://api.voicemod.net/api/v1/effects/apply"
    
    headers = {
        "X-API-Key": VOICEMOD_API_KEY,
        "Content-Type": "audio/ogg"
    }
    
    params = {
        "effect": effect_api_name
    }
    
    try:
        response = requests.post(
            url, 
            headers=headers, 
            params=params,
            data=audio_bytes,
            timeout=30
        )
        
        if response.status_code == 200:
            return io.BytesIO(response.content)
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Voice effect error: {e}")
        return None

# === TELEGRAM BOT HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when /start is issued."""
    welcome_text = (
        "🎙️ *Welcome to Voice Changer Bot!*\n\n"
        "I can transform your voice with awesome effects!\n\n"
        "*How to use:*\n"
        "1️⃣ Send me a voice message\n"
        "2️⃣ I'll apply an effect and send it back\n"
        "3️⃣ Use /effects to see all available effects\n"
        "4️⃣ Use /effect <name> to set your default effect\n\n"
        "*Quick example:*\n"
        "Send a voice message with caption 'robot' to apply robot effect!\n\n"
        "*Current default effect:* `magic-chords`\n"
        "Use /effects to see all 20+ effects! 🎭"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def show_effects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available voice effects with inline keyboard"""
    all_effects = effects.get_all_effects()
    
    # Create effect list for message
    effect_list = []
    for effect_name in all_effects[:15]:  # Show first 15 in text
        effect = effects.get_effect(effect_name)
        effect_list.append(f"{effect['name']} - `{effect_name}`")
    
    effect_text = "\n".join(effect_list)
    
    message = (
        "*🎭 Available Voice Effects:*\n\n"
        f"{effect_text}\n\n"
        f"*+ {len(all_effects) - 15} more effects!*\n\n"
        "*To use:*\n"
        "• Set default: `/effect robot`\n"
        "• One-time use: Send voice with caption 'robot'\n\n"
        "*Current default:* `{0}`"
    ).format(effects.get_user_effect(update.effective_user.id))
    
    # Create inline keyboard with effect buttons
    keyboard = []
    row = []
    for i, effect_name in enumerate(all_effects[:8]):  # Show 8 in buttons
        effect = effects.get_effect(effect_name)
        row.append(InlineKeyboardButton(
            effect['name'], 
            callback_data=f"set_effect_{effect_name}"
        ))
        if len(row) == 2:  # 2 buttons per row
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    # Add reset button
    keyboard.append([InlineKeyboardButton("🔄 Reset to Default", callback_data="set_effect_default")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)

async def set_effect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set default effect for user"""
    if not context.args:
        await update.message.reply_text(
            "❌ Please specify an effect!\n"
            "Usage: `/effect robot`\n"
            "Use /effects to see all effects.",
            parse_mode='Markdown'
        )
        return
    
    effect_name = context.args[0].lower()
    
    if effect_name in effects.get_all_effects():
        effects.set_user_effect(update.effective_user.id, effect_name)
        effect = effects.get_effect(effect_name)
        await update.message.reply_text(
            f"✅ Default effect set to: {effect['name']}\n"
            f"Send me a voice message to hear it!"
        )
    else:
        await update.message.reply_text(
            f"❌ Effect '{effect_name}' not found!\n"
            "Use /effects to see all available effects."
        )

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process voice message with effect"""
    
    # Determine which effect to use
    # Priority: 1. Caption text, 2. User default, 3. Global default
    effect = effects.DEFAULT_EFFECT
    
    # Check if user specified effect in caption
    if update.message.caption:
        caption_effect = update.message.caption.lower().strip()
        if caption_effect in effects.get_all_effects():
            effect = caption_effect
    
    # If no caption effect, use user's default
    if effect == effects.DEFAULT_EFFECT:
        user_effect = effects.get_user_effect(update.effective_user.id)
        if user_effect:
            effect = user_effect
    
    effect_name = effects.get_effect(effect)
    if effect_name:
        effect_display = effect_name['name']
    else:
        effect_display = effect
    
    # Send processing message
    processing_msg = await update.message.reply_text(
        f"🎛️ Processing your voice with **{effect_display}** effect...",
        parse_mode='Markdown'
    )
    
    try:
        # Download voice message
        voice_file = update.message.voice
        audio_bytes = download_voice_file(voice_file.file_id)
        
        if not audio_bytes:
            await processing_msg.edit_text("❌ Failed to download voice message. Please try again.")
            return
        
        # Apply voice effect
        processed_audio = apply_voice_effect(audio_bytes.getvalue(), effect)
        
        if not processed_audio:
            await processing_msg.edit_text(
                "❌ Failed to apply effect. Please try again with a shorter voice message (max 30 seconds)."
            )
            return
        
        # Send processed voice back
        await update.message.reply_voice(
            voice=processed_audio,
            caption=f"✨ Your voice with **{effect_display}** effect!\nUse /effects to try others!",
            parse_mode='Markdown'
        )
        
        await processing_msg.delete()
        
    except Exception as e:
        await processing_msg.edit_text(f"❌ Error: {str(e)}\nPlease try again with a shorter voice message.")
        print(f"Error processing voice: {e}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard callbacks"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("set_effect_"):
        effect_name = query.data.replace("set_effect_", "")
        
        if effect_name == "default":
            effect_name = effects.DEFAULT_EFFECT
        
        if effect_name in effects.get_all_effects() or effect_name == effects.DEFAULT_EFFECT:
            effects.set_user_effect(query.from_user.id, effect_name)
            effect = effects.get_effect(effect_name) if effect_name != effects.DEFAULT_EFFECT else {"name": "Magic Chords"}
            await query.edit_message_text(
                f"✅ Default effect set to: {effect['name'] if effect_name != effects.DEFAULT_EFFECT else 'Magic Chords'}\n"
                f"Send me a voice message to hear it!"
            )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message."""
    help_text = (
        "*🤖 Voice Changer Bot Help*\n\n"
        "*Commands:*\n"
        "/start - Welcome message\n"
        "/help - Show this help\n"
        "/effects - List all voice effects\n"
        "/effect <name> - Set default effect\n\n"
        "*How to use:*\n"
        "• Send voice message with caption = effect name (one-time)\n"
        "• Set default with /effect, then just send voice\n"
        "• Choose from 20+ effects!\n\n"
        "*Examples:*\n"
        "• `/effect robot` - Set robot as default\n"
        "• Send voice with caption 'alien' - Apply alien effect once\n\n"
        "*Tip:* Effects work best with clear speech and < 30 seconds!"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    print(f"Error: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "An error occurred. Please try again later."
        )

# === MAIN FUNCTION ===
async def main():
    """Initialize and run the Telegram bot."""
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("effects", show_effects))
    application.add_handler(CommandHandler("effect", set_effect))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_error_handler(error_handler)
    
    # Start bot with polling
    print("🎤 Voice Changer Bot is starting...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    print("✅ Voice Changer Bot is running successfully!")
    
    # Keep bot running
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

# === ENTRY POINT ===
if __name__ == "__main__":
    import asyncio
    import threading
    
    # Run Flask in a separate thread for health checks
    def run_flask():
        flask_app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
    
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    # Run the bot
    try:
        asyncio.run(main())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
