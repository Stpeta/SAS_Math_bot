import asyncio
import logging
import sqlite3

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from anthropic import AsyncAnthropic

from config_data.avatars import avatars
from config_data.config import (Config, load_config)
from keyboards.main_menu import set_main_menu

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(filename)s:%(lineno)d #%(levelname)-8s '
           '[%(asctime)s] - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# Load the config into the config variable
config: Config = load_config()

# Initialize bot and dispatcher
bot = Bot(token=config.tg_bot.token)
dp = Dispatcher()

# Initialize AsyncAnthropic client
anthropic_client = AsyncAnthropic(api_key=config.tg_bot.anthropic_api_key)

# Initialize SQLite database
conn = sqlite3.connect('chat_history.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat_history
    (user_id INTEGER, message_text TEXT, role TEXT)
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_avatars
    (user_id INTEGER PRIMARY KEY, avatar TEXT)
''')
conn.commit()

# Constants
MAX_DIALOGUE_LENGTH = config.tg_bot.max_dialogue_length  # Maximum number of characters in a dialogue


# Database functions
def add_message_to_db(user_id, message_text, role):
    cursor.execute('INSERT INTO chat_history VALUES (?, ?, ?)', (user_id, message_text, role))
    conn.commit()


def get_chat_history(user_id):
    cursor.execute('SELECT message_text, role FROM chat_history WHERE user_id = ? ORDER BY rowid', (user_id,))
    return cursor.fetchall()


def clear_chat_history(user_id):
    cursor.execute('DELETE FROM chat_history WHERE user_id = ?', (user_id,))
    conn.commit()


def set_user_avatar(user_id, avatar):
    cursor.execute('INSERT OR REPLACE INTO user_avatars VALUES (?, ?)', (user_id, avatar))
    conn.commit()


def get_user_avatar(user_id):
    cursor.execute('SELECT avatar FROM user_avatars WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    return result[0] if result else None


# Create inline keyboard for avatar selection
def get_avatar_keyboard():
    keyboard = []
    for avatar in avatars.keys():
        keyboard.append([InlineKeyboardButton(text=avatar, callback_data=f"avatar_{avatar}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    clear_chat_history(user_id)
    await message.reply("Welcome! Please select the person you'd like to talk to:", reply_markup=get_avatar_keyboard())
    logger.info(f"New chat started for user {user_id}")


@dp.message(Command('help'))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    clear_chat_history(user_id)
    await message.reply("This bot allows you to speak with a great mathematician. \n\n Author: @nedanaec")
    logger.info(f"Command /help was sent by user {user_id}")


@dp.callback_query(lambda c: c.data and c.data.startswith('avatar_'))
async def process_avatar_selection(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    selected_avatar = callback_query.data.split('_')[1]
    set_user_avatar(user_id, selected_avatar)
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(user_id, f"You've selected to talk with {selected_avatar}.")
    logger.info(f"User {user_id} selected avatar: {selected_avatar}")


@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    user_message = message.text
    user_avatar = get_user_avatar(user_id)

    if not user_avatar:
        await message.reply("Please select a person to talk by using the /start command.")
        return

    # Add user message to database
    add_message_to_db(user_id, user_message, 'user')

    # Get chat history
    history = get_chat_history(user_id)

    # Check if dialogue length exceeds the limit
    dialogue_length = sum(len(msg[0]) for msg in history)
    if dialogue_length > MAX_DIALOGUE_LENGTH:
        clear_chat_history(user_id)
        await message.reply("The conversation has reached its length limit. Starting a new conversation with the same "
                            "person.")
        logger.info(f"Dialogue limit reached for user {user_id}. Starting new conversation.")
        return

    # Prepare messages for Claude
    claude_messages = [{"role": msg[1], "content": msg[0]} for msg in history]

    try:
        # Get response from Claude
        response = await anthropic_client.messages.create(
            model=config.tg_bot.ai_model,
            max_tokens=config.tg_bot.max_tokens,
            system=avatars[user_avatar],
            messages=claude_messages
        )

        claude_response = response.content[0].text

        # Add Claude's response to database
        add_message_to_db(user_id, claude_response, 'assistant')

        # Send response to user
        await message.reply(claude_response)
        logger.info(f"Sent response to user {user_id}")

    except Exception as e:
        logger.error(f"Error processing message for user {user_id}: {str(e)}")
        await message.reply(
            "I'm sorry, but I encountered an error while processing your message. Please try again later.")


async def main():
    try:
        logger.info("Starting bot")
        await set_main_menu(bot)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        conn.close()


if __name__ == '__main__':
    asyncio.run(main())
