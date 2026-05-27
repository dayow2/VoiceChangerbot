import os
import io
import asyncio
import threading
import requests
from flask import Flask, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from pydub import AudioSegment
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# === CONFIGURATION ===
TOKEN = os.environ.get("TELEGRAM_TOKEN")
PORT = int(os.environ.get("PORT", 5000))

# Voice effects database (simplified - no external API needed)
VOICE_EFFECTS = {
    "robot": {"name": "🤖 Robot", "desc": "Metallic voice"},
    "alien": {"name": "👽 Alien", "desc": "Extraterrestrial"},
    "helium": {"name": "🎈 Helium", "desc": "High-pitched"},
    "demon": {"name": "😈 Demon", "desc": "Deep voice"},
    "baby": {"name": "🍼 Baby", "desc": "Cute voice"},
    "echo": {"name": "🔄 Echo", "desc": "Repeating effect"},
    "slow": {"name": "🐢 Slow", "desc": "Slowed down"},
    "fast": {"name": "⚡ Fast", "desc": "Sped up"}
}

# User preferences
user_preferences = {}

# === FLASK APP ===
flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health_check():
    return jsonify({"status": "ok", "service": "Voice Changer Bot"}), 200

# === SIMPLE VOICE EFFECTS (No API required) ===
def apply_simple_effect(audio_bytes, effect_name):
    """Apply basic audio effects using pydub"""
    try:
        # Load audio
        audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="ogg")
        
        # Apply effects
        if effect_name == "slow":
            audio = audio.speedup(playback_speed=0.7)
        elif effect_name == "fast":
            audio = audio.speedup(playback_speed=1.5)
        elif effect_name == "echo":
            # Simple echo by overlapping
            echo = audio - 10  # Reduce volume
            audio = audio.overlay(echo, position=200)
        elif effect_name == "robot":
            # Add distortion effect
            audio = audio.low_pass_filter(1000).high_pass_filter(500)
        elif effect_name == "helium":
            # Speed up slightly for helium effect
            audio = audio.speedup(playback_speed=1.2)
        elif effect_name == "demon":
            # Slow down and add bass
            audio = audio.speedup(playback_speed=0.8).low_pass_filter(300)
        
        # Export to bytes
        output = io.BytesIO()
        audio.export(output, format="ogg")
        output.seek(0)
        return output
    except Exception as e:
        print(f"Effect error: {e}")
        return None

def download_voice(file_id):
    """Download voice message from Telegram"""
    url = f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}"
    response = requests.get(url).json()
    
    if not response.get('ok'):
        return None
    
    file_path = response['result']['file_path']
    file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
    
    audio_response = requests.get(file_url)
    return io.BytesIO(audio_response.content)

# === TELEGRAM HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "🎙️ *Welcome to Voice Changer Bot!*\n\n"
        "*How to use:*\n"
        "1️⃣ Send me a voice message\n"
        "2️⃣ I'll apply an effect and send it back\n"
        "3️⃣ Use /effects to see all effects\n"
        "4️⃣ Use /effect <name> to set default\n\n"
        "*Quick example:*\n"
        "Send voice with caption 'robot'\n\n"
        "*Available effects:*\n"
        "robot, alien, helium, demon, baby, echo, slow, fast\n\n"
        "Use /help for more info!"
    )
    await update.message.reply_text(welcome, parse_mode='Markdown')

async def show_effects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    effects_list = "\n".join([f"• `{name}` - {data['name']}" for name, data in VOICE_EFFECTS.items()])
    
    message = (
        "*🎭 Available Voice Effects:*\n\n"
        f"{effects_list}\n\n"
        "*To use:*\n"
        "• Set default: `/effect robot`\n"
        "• One-time: Send voice with caption 'robot'\n\n"
        f"*Current default:* `{user_preferences.get(str(update.effective_user.id), 'None')}`"
    )
    
    # Create inline keyboard
    keyboard = []
    row = []
    for name, data in list(VOICE_EFFECTS.items())[:4]:
        row.append(InlineKeyboardButton(data['name'], callback_data=f"effect_{name}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)

async def set_effect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: `/effect robot`\n"
            "Use /effects to see all effects.",
            parse_mode='Markdown'
        )
        return
    
    effect_name = context.args[0].lower()
    
    if effect_name in VOICE_EFFECTS:
        user_preferences[str(update.effective_user.id)] = effect_name
        await update.message.reply_text(
            f"✅ Default effect set to: {VOICE_EFFECTS[effect_name]['name']}\n"
            "Send me a voice message to hear it!"
        )
    else:
        await update.message.reply_text(
            f"❌ Effect '{effect_name}' not found!\n"
            "Use /effects to see all available effects."
        )

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Determine which effect to use
    effect = user_preferences.get(str(update.effective_user.id))
    
    # Check if user specified effect in caption
    if update.message.caption:
        caption_effect = update.message.caption.lower().strip()
        if caption_effect in VOICE_EFFECTS:
            effect = caption_effect
    
    if not effect:
        await update.message.reply_text(
            "🎙️ Please specify an effect!\n\n"
            "• Send voice with caption 'robot'\n"
            "• Or set default: `/effect robot`\n"
            "• See all: /effects",
            parse_mode='Markdown'
        )
        return
    
    effect_name = VOICE_EFFECTS.get(effect, {}).get('name', effect)
    
    # Send processing message
    processing = await update.message.reply_text(f"🎛️ Applying **{effect_name}** effect...", parse_mode='Markdown')
    
    try:
        # Download voice
        voice = update.message.voice
        audio_bytes = download_voice(voice.file_id)
        
        if not audio_bytes:
            await processing.edit_text("❌ Failed to download voice. Try again!")
            return
        
        # Apply effect
        processed = apply_simple_effect(audio_bytes.getvalue(), effect)
        
        if not processed:
            await processing.edit_text("❌ Failed to apply effect. Try a shorter message!")
            return
        
        # Send result
        await update.message.reply_voice(
            voice=processed,
            caption=f"✨ Your voice with **{effect_name}** effect!\nUse /effects to try others!",
            parse_mode='Markdown'
        )
        
        await processing.delete()
        
    except Exception as e:
        await processing.edit_text(f"❌ Error: {str(e)[:50]}")
        print(f"Error: {e}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("effect_"):
        effect_name = query.data.replace("effect_", "")
        user_preferences[str(query.from_user.id)] = effect_name
        await query.edit_message_text(
            f"✅ Default effect set to: {VOICE_EFFECTS[effect_name]['name']}\n"
            "Send me a voice message to hear it!"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "*🤖 Voice Changer Bot Help*\n\n"
        "*Commands:*\n"
        "/start - Welcome message\n"
        "/help - Show this help\n"
        "/effects - List all voice effects\n"
        "/effect <name> - Set default effect\n\n"
        "*How to use:*\n"
        "• Send voice message with caption = effect name\n"
        "• Set default with /effect, then just send voice\n\n"
        "*Examples:*\n"
        "• `/effect robot` - Set robot as default\n"
        "• Send voice with caption 'alien' - Apply alien effect\n\n"
        "*Available effects:*\n"
        "robot, alien, helium, demon, baby, echo, slow, fast"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Error: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("An error occurred. Please try again.")

# === MAIN ===
async def main():
    """Initialize and run bot"""
    if not TOKEN:
        print("❌ TELEGRAM_TOKEN environment variable not set!")
        return
    
    print(f"🤖 Starting Voice Changer Bot...")
    print(f"📍 Token: {TOKEN[:10]}...")
    
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
    
    # Start bot
    print("✅ Bot handlers registered")
    print("🚀 Starting polling...")
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    print("✅ Bot is running successfully!")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        print("\n⏹️ Stopping bot...")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

# === ENTRY POINT ===
if __name__ == "__main__":
    # Run Flask in background thread
    def run_flask():
        flask_app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print(f"✅ Flask health check server running on port {PORT}")
    
    # Run bot
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Fatal error: {e}")
