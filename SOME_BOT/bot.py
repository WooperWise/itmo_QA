"""
Main Telegram bot for QA with RAG capabilities.
"""

import asyncio
import logging
import os
import time
from typing import List

from constants import MAX_MESSAGE_LENGTH, TELEGRAM_BOT_TOKEN, get_message
from services.conversation_service import ConversationService
from services.rag_service import RAGService
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from utils.language_utils import get_response_language
from utils.logging_utils import (
    log_error_with_context,
    log_user_interaction,
    setup_logging,
)
from utils.message_utils import (
    clean_think_sections,
    filter_think_blocks,
    log_full_response,
    prepare_messages_with_sources,
)

# Setup logging
setup_logging("INFO")
logger = logging.getLogger(__name__)

# Get database path from environment
DATABASE_PATH = os.getenv("DATABASE_PATH", "conversations.db")

# Initialize services
rag_service = RAGService()
conversation_service = ConversationService(DATABASE_PATH)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    language = get_response_language(update.message.text)

    logger.info(f"User {user.username} ({user.id}) started the bot")

    start_message = get_message("start", language)

    await update.message.reply_text(start_message, parse_mode=ParseMode.MARKDOWN)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    user = update.effective_user
    language = get_response_language(update.message.text)

    logger.info(f"User {user.username} ({user.id}) requested help")

    help_message = get_message("help", language)

    await update.message.reply_text(help_message, parse_mode=ParseMode.MARKDOWN)


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /history command - show recent conversation history."""
    user = update.effective_user
    language = get_response_language(update.message.text)

    logger.info(f"User {user.username} ({user.id}) requested conversation history")

    try:
        # Get recent conversations from the service
        recent_exchanges = conversation_service.get_recent_conversations(
            user.id, limit=3
        )

        if not recent_exchanges:
            if language == "ru":
                no_history_msg = "📝 У вас пока нет истории разговоров. Задайте мне вопрос, чтобы начать!"
            else:
                no_history_msg = "📝 You don't have any conversation history yet. Ask me a question to get started!"

            await update.message.reply_text(no_history_msg)
            return

        # Format the conversation history
        if language == "ru":
            history_text = "📝 **Ваша недавняя история разговоров:**\n\n"
        else:
            history_text = "📝 **Your Recent Conversation History:**\n\n"

        for i, exchange in enumerate(recent_exchanges, 1):
            if language == "ru":
                history_text += f"**Обмен {i}:**\n"
            else:
                history_text += f"**Exchange {i}:**\n"

            # Add user question
            if "user" in exchange:
                user_msg = exchange["user"]["content"]
                # Truncate long messages
                if len(user_msg) > 200:
                    user_msg = user_msg[:200] + "..."
                if language == "ru":
                    history_text += f"👤 **Вы:** {user_msg}\n"
                else:
                    history_text += f"👤 **You:** {user_msg}\n"

            # Add bot response
            if "bot" in exchange:
                bot_msg = exchange["bot"]["content"]
                # Truncate long responses
                if len(bot_msg) > 300:
                    bot_msg = bot_msg[:300] + "..."
                if language == "ru":
                    history_text += f"🤖 **Бот:** {bot_msg}\n"
                else:
                    history_text += f"🤖 **Bot:** {bot_msg}\n"

            history_text += "\n"

        # Split message if too long
        if len(history_text) > MAX_MESSAGE_LENGTH:
            parts = [
                history_text[i : i + MAX_MESSAGE_LENGTH]
                for i in range(0, len(history_text), MAX_MESSAGE_LENGTH)
            ]
            for part in parts:
                await update.message.reply_text(part, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(history_text, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error retrieving conversation history for {user.username}: {e}")
        if language == "ru":
            error_msg = "❌ Произошла ошибка при получении истории разговоров."
        else:
            error_msg = "❌ An error occurred while retrieving conversation history."
        await update.message.reply_text(error_msg)


async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /health command (for debugging)."""
    user = update.effective_user

    if user.id not in []:  # Add admin user IDs here if needed
        logger.warning(
            f"Non-admin user {user.username} ({user.id}) tried to access health"
        )
        return

    logger.info(f"Admin {user.username} ({user.id}) requested health check")

    health_status = rag_service.health_check()

    status_text = "🏥 **System Health Status**\n\n"

    for component, status in health_status.items():
        emoji = "✅" if status else "❌"
        status_text += (
            f"{emoji} {component.title()}: {'Healthy' if status else 'Unhealthy'}\n"
        )

    # Add conversation service health
    conv_health = conversation_service.health_check()
    emoji = "✅" if conv_health else "❌"
    status_text += (
        f"{emoji} Conversation Service: {'Healthy' if conv_health else 'Unhealthy'}\n"
    )

    await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)


async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user questions."""
    user = update.effective_user
    query = update.message.text.strip()

    if not query:
        return

    # Detect language
    language = get_response_language(query)

    logger.info(
        f"User {user.username} ({user.id}) asked: '{query[:100]}...' in {language}"
    )

    # Store user message in conversation history
    try:
        conversation_service.store_message(user.id, "user", query)
        logger.debug(f"Stored user message for {user.id}")
    except Exception as e:
        logger.error(f"Failed to store user message: {e}")

    # Send processing message
    processing_message = get_message("processing", language)
    processing_msg = await update.message.reply_text(processing_message)

    start_time = time.time()

    try:
        # Get answer from RAG service
        answer, sources = rag_service.answer_question(query, language, user.id)

        if not answer:
            # No answer generated
            error_message = get_message("no_content", language)
            await processing_msg.edit_text(error_message)
            return

        # Log <tool_call> blocks separately but keep them in the response
        original_answer, think_blocks = filter_think_blocks(answer)

        # Log the complete response before sending
        log_full_response(answer, sources, think_blocks)

        # Prepare messages with sources - use raw answer without filtering
        messages = prepare_messages_with_sources(
            answer, sources, language, MAX_MESSAGE_LENGTH
        )

        # Send messages as plain text (no Markdown parsing)
        if messages:
            # Edit the processing message with the first part
            await processing_msg.edit_text(messages[0], disable_web_page_preview=True)

            # Send additional messages if needed
            for message in messages[1:]:
                await update.message.reply_text(message, disable_web_page_preview=True)

        # Store bot response in conversation history (cleaned)
        try:
            # Combine all messages for storage
            full_response = "\n\n".join(messages) if messages else answer
            # Clean the response before storing
            cleaned_response = clean_think_sections(full_response)
            conversation_service.store_message(user.id, "bot", cleaned_response)
            logger.debug(f"Stored bot response for {user.id}")
        except Exception as e:
            logger.error(f"Failed to store bot response: {e}")

        duration = time.time() - start_time

        # Log successful interaction
        log_user_interaction(
            user.id, user.username or "unknown", query, len(messages), duration
        )

        logger.info(
            f"Successfully answered question for {user.username} in {duration:.2f}s"
        )

    except Exception as e:
        duration = time.time() - start_time

        # Log error
        log_error_with_context(
            e,
            {"query_length": len(query), "language": language, "duration": duration},
            user.id,
        )

        # Send error message
        error_message = get_message("error", language)
        try:
            await processing_msg.edit_text(error_message)
        except:
            await update.message.reply_text(error_message)

        logger.error(f"Error handling question from {user.username}: {e}")


async def handle_service_error(
    update: Update, context: ContextTypes.DEFAULT_TYPE, error_type: str
) -> None:
    """Handle service-specific errors."""
    language = get_response_language(update.message.text)

    if error_type == "qdrant":
        error_message = get_message("qdrant_error", language)
    elif error_type == "ollama":
        error_message = get_message("ollama_error", language)
    else:
        error_message = get_message("error", language)

    await update.message.reply_text(error_message)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors in the bot."""
    logger.error(f"Exception while handling an update: {context.error}")

    # Try to send error message to user if possible
    if isinstance(update, Update) and update.effective_message:
        try:
            language = get_response_language(update.effective_message.text or "")
            error_message = get_message("error", language)
            await update.effective_message.reply_text(error_message)
        except:
            pass  # Don't fail if we can't send error message


def main() -> None:
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        return

    logger.info("Starting QA Telegram Bot...")

    # Check RAG service health
    health_status = rag_service.health_check()
    if not health_status.get("overall", False):
        logger.warning("RAG service is not fully healthy, but starting bot anyway")
        logger.warning(f"Health status: {health_status}")
    else:
        logger.info("RAG service is healthy")

    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("health", health_command))

    # Handle all text messages as questions
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question)
    )

    # Add error handler
    application.add_error_handler(error_handler)

    logger.info("Bot handlers registered, starting polling...")

    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
