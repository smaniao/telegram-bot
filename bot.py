import sqlite3
import pandas as pd
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from datetime import datetime

TOKEN = "YOUR_BOT_TOKEN"
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Подключение к базе данных
conn = sqlite3.connect("queue.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    truck_number TEXT,
    direction TEXT,
    registered_at TEXT,
    arrived_at TEXT,
    left_at TEXT
)
""")
conn.commit()

# Хранилище для ожидающих ввода
waiting_for = {}

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = message.from_user.id
    if cursor.execute("SELECT * FROM queue WHERE user_id=?", (user_id,)).fetchone():
        await message.reply("Вы уже зарегистрированы в очереди.")
    else:
        waiting_for[user_id] = "truck_number"
        await message.reply("Введите номер вашего автомобиля:")

@dp.message_handler(lambda message: message.from_user.id in waiting_for)
async def process_registration(message: types.Message):
    user_id = message.from_user.id
    step = waiting_for[user_id]

    if step == "truck_number":
        waiting_for[user_id] = {"truck_number": message.text}
        await message.reply("Введите направление (например, Москва, Варшава):")

    elif step == "direction":
        data = waiting_for.pop(user_id)
        truck_number = data["truck_number"]
        direction = message.text
        registered_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("INSERT INTO queue (user_id, username, truck_number, direction, registered_at) VALUES (?, ?, ?, ?, ?)",
                       (user_id, message.from_user.username, truck_number, direction, registered_at))
        conn.commit()

        await message.reply(f"Вы добавлены в очередь. \nНомер авто: {truck_number} \nНаправление: {direction}")

@dp.message_handler(commands=["next"])
async def next_driver(message: types.Message):
    cursor.execute("SELECT * FROM queue ORDER BY id ASC LIMIT 1")
    driver = cursor.fetchone()

    if driver:
        user_id, _, username, truck_number, direction, registered_at, _, _ = driver
        arrived_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("UPDATE queue SET arrived_at=? WHERE user_id=?", (arrived_at, user_id))
        conn.commit()

        await bot.send_message(user_id, "Ваша очередь! Подъезжайте к загрузке.")
        await message.reply(f"Вызван водитель: {truck_number} ({direction})")

@dp.message_handler(commands=["leave"])
async def leave_queue(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("DELETE FROM queue WHERE user_id=?", (user_id,))
    conn.commit()
    await message.reply("Вы удалены из очереди.")

@dp.message_handler(commands=["export"])
async def export_to_excel(message: types.Message):
    df = pd.read_sql("SELECT * FROM queue", conn)
    file_path = "queue_data.xlsx"
    df.to_excel(file_path, index=False)

    with open(file_path, "rb") as file:
        await message.reply_document(file)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
