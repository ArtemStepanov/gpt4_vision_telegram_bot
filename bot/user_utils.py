import asyncio
from datetime import datetime
from telegram import Update, User
from telegram.ext import CallbackContext

import config
from database import Database


class UserUtils:
    user_semaphores = {}
    user_tasks = {}

    def __init__(self, db):
        self.db: Database = db

    async def register_user_if_not_exists(
        self, update: Update, context: CallbackContext, user: User
    ):
        if not await self.db.check_if_user_exists(user.id):
            await self.db.add_new_user(
                user.id,
                update.message.chat_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
            )
            await self.db.start_new_dialog(user.id)

        if await self.db.get_user_attribute(user.id, "current_dialog_id") is None:
            await self.db.start_new_dialog(user.id)

        if user.id not in self.user_semaphores:
            self.user_semaphores[user.id] = asyncio.Semaphore(1)

        if await self.db.get_user_attribute(user.id, "current_model") is None:
            await self.db.set_user_attribute(
                user.id, "current_model", config.models["available_text_models"][0]
            )

        # back compatibility for n_used_tokens field
        n_used_tokens = await self.db.get_user_attribute(user.id, "n_used_tokens")
        if isinstance(n_used_tokens, int) or isinstance(
            n_used_tokens, float
        ):  # old format
            new_n_used_tokens = {
                "gpt-3.5-turbo": {"n_input_tokens": 0, "n_output_tokens": n_used_tokens}
            }
            await self.db.set_user_attribute(
                user.id, "n_used_tokens", new_n_used_tokens
            )

        # voice message transcription
        if await self.db.get_user_attribute(user.id, "n_transcribed_seconds") is None:
            await self.db.set_user_attribute(user.id, "n_transcribed_seconds", 0.0)

        # image generation
        if await self.db.get_user_attribute(user.id, "n_generated_images") is None:
            await self.db.set_user_attribute(user.id, "n_generated_images", 0)

    async def update_user_last_interaction(self, user_id):
        await self.db.set_user_attribute(user_id, "last_interaction", datetime.now())

    async def get_current_chat_mode(self, user_id) -> str:
        return await self.db.get_user_attribute(user_id, "current_chat_mode")

    async def get_last_interaction(self, user_id) -> datetime:
        return await self.db.get_user_attribute(user_id, "last_interaction")

    async def get_dialog_messages(self, user_id) -> list:
        dialog_id = await self.db.get_user_attribute(user_id, "current_dialog_id")
        return await self.db.get_dialog_messages(user_id, dialog_id)

    async def start_new_dialog(self, user_id):
        await self.db.start_new_dialog(user_id)

    async def get_current_model(self, user_id) -> str:
        return await self.db.get_user_attribute(user_id, "current_model")

    async def set_current_model(self, user_id, model):
        await self.db.set_user_attribute(user_id, "current_model", model)

    async def set_dialog_messages(self, user_id, messages):
        dialog_id = await self.db.get_user_attribute(user_id, "current_dialog_id")
        await self.db.set_dialog_messages(user_id, messages, dialog_id)

    async def update_n_used_tokens(
        self, user_id, model, n_input_tokens, n_output_tokens
    ):
        await self.db.update_n_used_tokens(
            user_id, model, n_input_tokens, n_output_tokens
        )

    async def update_n_transcribed_seconds(self, user_id, n_transcribed_seconds):
        await self.db.set_user_attribute(
            user_id,
            "n_transcribed_seconds",
            n_transcribed_seconds
            + await self.db.get_user_attribute(user_id, "n_transcribed_seconds"),
        )

    async def set_n_generated_images(self, user_id, n_generated_images):
        await self.db.set_user_attribute(
            user_id, "n_generated_images", n_generated_images
        )

    async def get_n_generated_images(self, user_id) -> int:
        return await self.db.get_user_attribute(user_id, "n_generated_images")

    async def set_current_chat_mode(self, user_id, chat_mode):
        await self.db.set_user_attribute(user_id, "current_chat_mode", chat_mode)

    async def get_n_used_tokens(self, user_id) -> int:
        return await self.db.get_user_attribute(user_id, "n_used_tokens")

    async def get_n_transcribed_seconds(self, user_id) -> float:
        return await self.db.get_user_attribute(user_id, "n_transcribed_seconds")
