import telebot
from telebot import types
import requests

BOT_TOKEN = "YOUR_BOT_TOKEN"
API_URL = "http://localhost:8000"  # URL твоего backend

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Отправь список покупок через запятую.\nПример: Хлеб 50, Молоко 100")

@bot.message_handler(func=lambda message: True)
def create_check(message):
    buyer_id = message.from_user.id
    
    # Парсим список
    items = []
    try:
        for item in message.text.split(','):
            name, price = item.strip().rsplit(' ', 1)
            items.append({'name': name, 'price': float(price)})
    except:
        bot.reply_to(message, "Ошибка формата. Используй: Название 100, Название2 200")
        return
    
    # Создаем чек через API
    response = requests.post(f"{API_URL}/api/checks", json={
        'buyer_id': buyer_id,
        'items': items
    })
    
    if response.status_code == 200:
        check_id = response.json()['check_id']
        
        # Отправляем кнопку с Mini App
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            "🧾 Открыть приложение",
            web_app=types.WebAppInfo(url=f"https://your-domain.com/?check_id={check_id}")
        ))
        
        bot.send_message(
            message.chat.id,
            "Чек создан! Нажмите кнопку, чтобы распределить покупки:",
            reply_markup=markup
        )
    else:
        bot.reply_to(message, "Ошибка при создании чека")

if __name__ == '__main__':
    bot.infinity_polling()