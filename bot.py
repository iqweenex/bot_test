import aiosqlite
import asyncio
import logging
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

logging.basicConfig(level=logging.INFO)

API_TOKEN = '' #input your bot token here

DB_NAME = 'quiz_bot.db'

DICT_DATA = 'data/quiz_data.json'


bot = Bot(token=API_TOKEN)

dp = Dispatcher()

with open(DICT_DATA, 'r') as j:
    quiz_data = json.loads(j.read())

def generate_options_keyboard(answer_options, right_answer):
    builder = InlineKeyboardBuilder()

    for option in answer_options:
        builder.add(types.InlineKeyboardButton(
            text=option,
            callback_data='right_answer' if option==right_answer else 'wrong_answer'
        ))

    builder.adjust(1)
    return builder.as_markup()


@dp.callback_query(F.data=='right_answer')
async def right_answer(callback: types.CallbackQuery):

    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )

    await callback.message.answer("Верно!")
    current_question_index = await get_quiz_index(callback.from_user.id)
    current_score = await get_user_score(callback.from_user.id)
    current_question_index+=1
    current_score+=1
    await update_quiz_index(callback.from_user.id, current_question_index)
    await update_user_score(callback.from_user.id, current_score)

    if current_question_index <len(quiz_data):
        await(get_question(callback.message, callback.from_user.id))
    else:
        await callback.message.answer((f"Это был последний вопрос. Квиз завершен!\nВаш результат: {current_score} правильных ответов"))


@dp.callback_query(F.data=='wrong_answer')
async def wrong_answer(callback: types.CallbackQuery):
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.from_user.id,
        reply_markup=None
    )

    current_question_index = await get_quiz_index(callback.from_user.id)
    current_score = await get_user_score(callback.from_user.id)
    correct_option = quiz_data[current_question_index]['correct_option']

    await callback.message.answer(f"Неверно.\nВерный ответ {quiz_data[current_question_index]['options'][correct_option]}")

    current_question_index+=1
    await update_quiz_index(callback.from_user.id, current_question_index)
    await update_user_score(callback.from_user.id, current_score)

    if current_question_index < len(quiz_data):
        await get_question(callback.message, callback.from_user.id)
    else:
        await callback.message.answer(f"Это был последний вопрос. Квиз завершен\nВаш счет: {current_score}")


#Хэндлер на команду /start
@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text='Начать игру'))
    await message.answer('Добро пожаловать в квиз!', reply_markup=builder.as_markup(resize_keyboard=True))


async def get_question(message, user_id):
    #Получение текущего вопросы из словаря состояний пользователя
    current_question_index = await get_quiz_index(user_id)
    correct_index = quiz_data[current_question_index]['correct_option']
    opts = quiz_data[current_question_index]['options']
    kb = generate_options_keyboard(opts, opts[correct_index])
    await message.answer(f"{quiz_data[current_question_index]['question']}", reply_markup=kb)


async def new_quiz(message):
    user_id = message.from_user.id
    current_question_index = 0
    new_score = 0
    await update_quiz_index(user_id, current_question_index)
    await update_user_score(user_id, new_score)
    await get_question(message, user_id)


async def get_quiz_index(user_id):
    #Подключение к базе данных
    async with aiosqlite.connect(DB_NAME) as db:
        #Получаем запись для заданного пользователя
        async with db.execute("SELECT question_index FROM quiz_state WHERE user_id = (?)", (user_id, )) as cursor:
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0


async def get_user_score(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT score FROM users WHERE user_id = (?)", (user_id, )) as cursor:
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0


async def update_quiz_index(user_id, index):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO quiz_state (user_id, question_index) VALUES (?, ?)", (user_id, index))
        await db.commit()


async def update_user_score(user_id, new_score):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT INTO users (user_id, score) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET score = excluded.score', (user_id, new_score))
        await db.commit()


@dp.message(F.text == 'Начать игру')
@dp.message(Command('quiz'))
async def cmd_quiz(message: types.Message):
    await message.answer(f"Начнем!")
    await new_quiz(message)


async def create_table():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS quiz_state (user_id INTEGER PRIMARY KEY, question_index INTEGER''')
        await db.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, score INTEGER''')
        await db.commit()


@dp.message(Command("help"))
async def cmd_start(message: types.Message):
    await message.answer("Команды бота\n\start - начать взаимодействие с ботом\n\help - открыть помощь\n\quiz - начать игра")


async def main():
    await create_table()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
