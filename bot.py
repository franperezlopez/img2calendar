import html
import io
import json
import os
import tempfile
import traceback

from dotenv import load_dotenv
from loguru import logger
from telegram import InputFile, Update
from telegram.constants import ParseMode
from telegram.ext import (ApplicationBuilder, CallbackContext, CommandHandler,
                          ContextTypes, MessageHandler, Updater, filters)

from src.llm.agent import make_agent
from src.llm.callback_handler import OutputCallbackHandler


def process_image(image_url):
    logger.info("Processing image ...")
    agent = make_agent(callbacks=[OutputCallbackHandler()])
    event = agent.run(image_url)
    logger.info(event)
    return event


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get the image file from the message
    logger.info("Handling image ...")
    # user = update.message.from_user
    photo = await context.bot.get_file(update.message.document)

    # Download the image file and save it to a temporary file
    with tempfile.NamedTemporaryFile(delete=True) as f:
        image_path = f.name
        await photo.download_to_drive(image_path)

        # Process the image and generate the ICS file
        ics_data, action = process_image(image_path)

    # Send the ICS file to the user
    if ics_data:
        ics_file = InputFile(io.StringIO(ics_data), filename=f'{action}.ics')
        await update.message.reply_document(document=ics_file)
    else:
        await update.message.reply_text("No event found in image")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help for you ...")


async def echo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    await update.message.reply_text(update.message.text)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception(context.error)
    dev_chat_id = os.environ.get("TELEGRAM_DEV_CHAT_ID")
    if dev_chat_id:
        update_str = update.to_dict() if isinstance(update, Update) else str(update)
        tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
        tb_string = "".join(tb_list)
        message = (
            f"An exception was raised while handling an update\n"
            f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}" "</pre>\n\n"
            f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
            f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
            f"<pre>{html.escape(tb_string)}</pre>"
        )
        await context.bot.send_message(chat_id=dev_chat_id, text=message, parse_mode=ParseMode.HTML)


def main():
    # Set up the Telegram bot
    load_dotenv()
    app = ApplicationBuilder().token(os.environ["TELEGRAM_TOKEN"]).build()

    # Set up the message handler for images
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_command))
    app.add_handler(CommandHandler("help", help_command))

    app.add_error_handler(error_handler)

    # Start the bot
    logger.info("Starting bot ...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()