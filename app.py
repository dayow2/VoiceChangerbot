import os
import sys
import logging
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TOKEN = os.environ.get("TELEGRAM_TOKEN")
PORT = int(os.environ.get("PORT", 5000))

# Flask app for health checks
flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health():
    return "OK", 200

# Simple voice effects without pydub (to avoid issues)
def apply_effect(audio_file, effect):
    """Simple audio effect processing - returns same file for now"""
    # For now, just return the original file
    # This ensures the bot works even without complex audio processing
    return audio_file

# Bot handlers
async def start(update: Update, context):
    logger.info(f"User {update.effective_user.id} started bot")
    await update.message.reply_text(
        "🎙️ *Voice Changer Bot is Online!*\n\n"
        "Send me a voice message and I'll process it.\n\n"
        "*Commands:*\n"
        "/start - Start the bot\n"
        "/help - Show help\n"
        "/effects - List available effects\n\n"
        "*Note:* Voice effects are being added!",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context):
    await update.message.reply_text(
        "Send me a voice message and I'll reply with the processed audio!\n\n"
        "More effects coming soon!"
    )

async def effects(update: Update, context):
    await update.message.reply_text(
        "🎭 *Available Effects:*\n\n"
        "• Robot (coming soon)\n"
        "• Alien (coming soon)\n"
        "• Helium (coming soon)\n\n"
        "More effects being added daily!"
    )

async def handle_voice(update: Update, context):
    """Handle voice messages"""
    try:
        user = update.effective_user
        voice = update.message.voice
        
        logger.info(f"Received voice from {user.id}, duration: {voice.duration}s")
        
        # Get file info
        file = await context.bot.get_file(voice.file_id)
        
        # Download file
        audio_bytes = await file.download_as_bytearray()
        logger.info(f"Downloaded {len(audio_bytes)} bytes")
        
        # For now, just echo back the voice message
        # This proves the bot works
        await update.message.reply_voice(
            voice=bytes(audio_bytes),
            caption="✅ Your voice message received! Effects coming soon!"
        )
        
        logger.info(f"Sent voice back to {user.id}")
        
    except Exception as e:
        logger.error(f"Error handling voice: {e}")
        await update.message.reply_text(f"Error: {str(e)[:100]}")

async def error_handler(update, context):
    logger.error(f"Update {update} caused error {context.error}")

# Main function
async def main():
    logger.info("Starting bot...")
    
    if not TOKEN:
        logger.error("NO TOKEN! Set TELEGRAM_TOKEN environment variable")
        return
    
    logger.info(f"Token found: {TOKEN[:10]}...")
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("effects", effects))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_error_handler(error_handler)
    
    logger.info("Handlers registered")
    
    # Start bot
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    logger.info("Bot is running! 🚀")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Stopping bot...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

# Entry point
if __name__ == "__main__":
    import asyncio
    import threading
    
    # Run Flask in background
    def run_flask():
        flask_app.run(host='0.0.0.0', port=PORT)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Run bot
    asyncio.run(main())
