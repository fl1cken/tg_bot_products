from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from database import get_db, init_db
from models import CheckCreate, Item
import telebot

app = FastAPI()

# CORS для локальной разработки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Telegram Bot
BOT_TOKEN = "YOUR_BOT_TOKEN"
bot = telebot.TeleBot(BOT_TOKEN)

# Инициализация БД
init_db()

# Монтируем статические файлы (frontend)
app.mount("/static", StaticFiles(directory="../frontend"), name="static")

@app.get("/")
async def root():
    return FileResponse("../frontend/index.html")

@app.post("/api/users")
async def create_user(user_data: dict):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
        ''', (user_data['user_id'], user_data.get('username'), user_data.get('first_name')))
        conn.commit()
    return {"status": "ok"}

@app.post("/api/checks")
async def create_check(check_data: CheckCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Создаем чек
        cursor.execute('''
            INSERT INTO checks (buyer_id) VALUES (?)
        ''', (check_data.buyer_id,))
        check_id = cursor.lastrowid
        
        # Добавляем товары
        for item in check_data.items:
            cursor.execute('''
                INSERT INTO items (check_id, name, price) VALUES (?, ?, ?)
            ''', (check_id, item['name'], item['price']))
        
        conn.commit()
        
        # Отправляем сообщение в чат
        chat_id = -1001234567890  # ID вашего группового чата
        bot.send_message(
            chat_id,
            f"🧾 Новый чек! Откройте Mini App для распределения.",
            reply_markup=telebot.types.InlineKeyboardMarkup().add(
                telebot.types.InlineKeyboardButton(
                    "Открыть приложение",
                    web_app=telebot.types.WebAppInfo(url=f"https://your-domain.com/?check_id={check_id}")
                )
            )
        )
        
    return {"check_id": check_id}

@app.get("/api/checks/{check_id}")
async def get_check(check_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Получаем чек
        cursor.execute('SELECT * FROM checks WHERE id = ?', (check_id,))
        check = cursor.fetchone()
        
        if not check:
            raise HTTPException(status_code=404, detail="Check not found")
        
        # Получаем товары
        cursor.execute('SELECT * FROM items WHERE check_id = ?', (check_id,))
        items = cursor.fetchall()
        
        # Получаем владельцев для каждого товара
        items_with_owners = []
        for item in items:
            cursor.execute('''
                SELECT user_id FROM item_owners WHERE item_id = ?
            ''', (item['id'],))
            owners = [row['user_id'] for row in cursor.fetchall()]
            
            items_with_owners.append({
                'id': item['id'],
                'name': item['name'],
                'price': item['price'],
                'owners': owners
            })
        
        return {
            'id': check['id'],
            'buyer_id': check['buyer_id'],
            'status': check['status'],
            'items': items_with_owners
        }

@app.post("/api/items/{item_id}/owners")
async def add_owner(item_id: int, data: dict):
    user_id = data['user_id']
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Проверяем, не добавлен ли уже
        cursor.execute('''
            SELECT * FROM item_owners WHERE item_id = ? AND user_id = ?
        ''', (item_id, user_id))
        
        if cursor.fetchone():
            # Удаляем (toggle)
            cursor.execute('''
                DELETE FROM item_owners WHERE item_id = ? AND user_id = ?
            ''', (item_id, user_id))
        else:
            # Добавляем
            cursor.execute('''
                INSERT INTO item_owners (item_id, user_id) VALUES (?, ?)
            ''', (item_id, user_id))
        
        conn.commit()
    
    return {"status": "ok"}

@app.post("/api/checks/{check_id}/finish")
async def finish_check(check_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Получаем все товары
        cursor.execute('SELECT * FROM items WHERE check_id = ?', (check_id,))
        items = cursor.fetchall()
        
        debts = {}
        
        for item in items:
            # Получаем владельцев
            cursor.execute('''
                SELECT user_id FROM item_owners WHERE item_id = ?
            ''', (item['id'],))
            owners = cursor.fetchall()
            
            if not owners:
                # Если никто не взял, платит покупатель
                cursor.execute('SELECT buyer_id FROM checks WHERE id = ?', (check_id,))
                buyer_id = cursor.fetchone()['buyer_id']
                debts[buyer_id] = debts.get(buyer_id, 0) + item['price']
            else:
                # Делим на всех владельцев
                share = item['price'] / len(owners)
                for owner in owners:
                    user_id = owner['user_id']
                    debts[user_id] = debts.get(user_id, 0) + share
        
        # Обновляем статус чека
        cursor.execute('''
            UPDATE checks SET status = 'closed' WHERE id = ?
        ''', (check_id,))
        conn.commit()
        
        # Формируем результат
        result = []
        for user_id, debt in debts.items():
            cursor.execute('SELECT first_name FROM users WHERE user_id = ?', (user_id,))
            user = cursor.fetchone()
            name = user['first_name'] if user else f"User {user_id}"
            result.append({'name': name, 'debt': round(debt, 2)})
        
        # Отправляем результат в чат
        chat_id = -1001234567890
        message = "🧾 *Итоги чека:*\n\n"
        for item in result:
            message += f"👤 {item['name']}: {item['debt']} руб.\n"
        
        bot.send_message(chat_id, message, parse_mode='Markdown')
        
    return {"debts": result}