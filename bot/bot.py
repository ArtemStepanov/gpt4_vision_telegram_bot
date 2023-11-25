import logging

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    AIORateLimiter,
    filters,
)

import config
from database import Database
from user_utils import UserUtils
import handlers


# setup
_user = UserUtils(Database())
logger = logging.getLogger(__name__)


def get_chat_mode_menu(page_index: int) -> tuple[str, InlineKeyboardMarkup]:
    n_chat_modes_per_page = config.n_chat_modes_per_page
    text = f"Select <b>chat mode</b> ({len(config.chat_modes)} modes available):"

    # buttons
    chat_mode_keys = list(config.chat_modes.keys())
    page_chat_mode_keys = chat_mode_keys[
        page_index * n_chat_modes_per_page : (page_index + 1) * n_chat_modes_per_page
    ]

    keyboard = []
    for chat_mode_key in page_chat_mode_keys:
        name = config.chat_modes[chat_mode_key]["name"]
        keyboard.append(
            [InlineKeyboardButton(name, callback_data=f"set_chat_mode|{chat_mode_key}")]
        )

    # pagination
    if len(chat_mode_keys) > n_chat_modes_per_page:
        is_first_page = page_index == 0
        is_last_page = (page_index + 1) * n_chat_modes_per_page >= len(chat_mode_keys)

        if is_first_page:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "»", callback_data=f"show_chat_modes|{page_index + 1}"
                    )
                ]
            )
        elif is_last_page:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "«", callback_data=f"show_chat_modes|{page_index - 1}"
                    ),
                ]
            )
        else:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        "«", callback_data=f"show_chat_modes|{page_index - 1}"
                    ),
                    InlineKeyboardButton(
                        "»", callback_data=f"show_chat_modes|{page_index + 1}"
                    ),
                ]
            )

    reply_markup = InlineKeyboardMarkup(keyboard)

    return text, reply_markup


async def get_settings_menu(user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    current_model = await _user.get_current_model(user_id)
    text = config.models["info"][current_model]["description"]

    text += "\n\n"
    score_dict = config.models["info"][current_model]["scores"]
    for score_key, score_value in score_dict.items():
        text += "🟢" * score_value + "⚪️" * (5 - score_value) + f" – {score_key}\n\n"

    text += "\nSelect <b>model</b>:"

    # buttons to choose models
    buttons = []
    for model_key in config.models["available_text_models"]:
        title = config.models["info"][model_key]["name"]
        if model_key == current_model:
            title = "✅ " + title

        buttons.append(
            InlineKeyboardButton(title, callback_data=f"set_settings|{model_key}")
        )
    reply_markup = InlineKeyboardMarkup([buttons])

    return text, reply_markup


async def post_init(application: Application):
    await application.bot.set_my_commands(
        [
            BotCommand("/new", "Start new dialog"),
            BotCommand("/mode", "Select chat mode"),
            BotCommand("/retry", "Re-generate response for previous query"),
            BotCommand("/balance", "Show balance"),
            BotCommand("/settings", "Show settings"),
            BotCommand("/help", "Show help message"),
        ]
    )


def run_bot() -> None:
    application = (
        ApplicationBuilder()
        .token(config.telegram_token)
        .concurrent_updates(True)
        .rate_limiter(AIORateLimiter(max_retries=5))
        .http_version("1.1")
        .get_updates_http_version("1.1")
        .post_init(post_init)
        .build()
    )

    # add handlers
    user_filter = filters.ALL
    if len(config.allowed_telegram_usernames) > 0:
        usernames = [x for x in config.allowed_telegram_usernames if isinstance(x, str)]
        any_ids = [x for x in config.allowed_telegram_usernames if isinstance(x, int)]
        user_ids = [x for x in any_ids if x > 0]
        group_ids = [x for x in any_ids if x < 0]
        user_filter = (
            filters.User(username=usernames)
            | filters.User(user_id=user_ids)
            | filters.Chat(chat_id=group_ids)
        )

    application.add_handler(
        CommandHandler("start", handlers.start_handle, filters=user_filter)
    )
    application.add_handler(
        CommandHandler("help", handlers.help_handle, filters=user_filter)
    )

    application.add_handler(
        CommandHandler(
            "help_group_chat", handlers.help_group_chat_handle, filters=user_filter
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & user_filter, handlers.message_handle
        )
    )

    application.add_handler(
        CommandHandler("retry", handlers.retry_handle, filters=user_filter)
    )

    application.add_handler(
        CommandHandler("new", handlers.new_dialog_handle, filters=user_filter)
    )
    application.add_handler(
        CommandHandler("cancel", handlers.cancel_handle, filters=user_filter)
    )

    application.add_handler(
        MessageHandler(filters.VOICE & user_filter, handlers.voice_message_handle)
    )

    application.add_handler(
        MessageHandler(filters.PHOTO & user_filter, handlers.message_handle)
    )

    application.add_handler(
        CommandHandler("mode", handlers.show_chat_modes_handle, filters=user_filter)
    )
    application.add_handler(
        CallbackQueryHandler(
            handlers.show_chat_modes_callback_handle, pattern="^show_chat_modes"
        )
    )
    application.add_handler(
        CallbackQueryHandler(handlers.set_chat_mode_handle, pattern="^set_chat_mode")
    )

    application.add_handler(
        CommandHandler("settings", handlers.settings_handle, filters=user_filter)
    )
    application.add_handler(
        CallbackQueryHandler(handlers.set_settings_handle, pattern="^set_settings")
    )

    application.add_handler(
        CommandHandler("balance", handlers.show_balance_handle, filters=user_filter)
    )

    application.add_error_handler(handlers.error_handle)

    # start the bot
    application.run_polling()


if __name__ == "__main__":
    run_bot()
