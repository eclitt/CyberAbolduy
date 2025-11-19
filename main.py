import telebot
from telebot import types
from settings import BOT_TOKEN, ADMINS, NA_PARE, COMMANDS, user_states, RADIUS, saved_point # ПЕРЕДЕЛАТЬ ИМПОРТЫ
from messages import welcome_text, about_text, help_text, response_text, location_text
from geopos import is_in_radius_meters

bot = telebot.TeleBot(BOT_TOKEN)
@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        user_name = message.from_user.first_name
        print("Пользователь", user_name, "с айди", message.chat.id, "запустил бота")
        # Создаем клавиатуру с кнопками
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
        
        # Добавляем кнопки
        btn_help = types.KeyboardButton('❓ Помощь')
        btn_about = types.KeyboardButton('ℹ️ О боте')
        btn_online = types.KeyboardButton('🧾 Отметиться на паре')
        btn_ktest = types.KeyboardButton('📕Посмотреть журнал')
        btn_openjournal = types.KeyboardButton('📗 Достать журнал')
        btn_closejournal = types.KeyboardButton('📕 Спрятать журнал')
        markup.add(btn_help, btn_about, btn_online, btn_ktest, btn_openjournal,btn_closejournal)
        
        # Форматируем текст с именем пользователя
        formatted_welcome = welcome_text.format(user_name)

        bot.send_message(message.chat.id, formatted_welcome, reply_markup=markup)
        
    except Exception as e:
        print(f"Error in send_welcome: {e}")

@bot.message_handler(commands=['❓ Помощь'])
def send_help(message):
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['ℹ️ О боте'])
def send_about(message):
    bot.reply_to(message, about_text)



# Обработчик нажатия на кнопку "Отметица"
@bot.message_handler(func=lambda message: message.text == '🧾 Отметиться на паре')
def otmetica(message):
    if str(message.chat.id) in NA_PARE:
        bot.send_message(message.chat.id, "Вы уже отметились✅", parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, location_text, parse_mode='Markdown')


# Обработчик нажатия на кнопку "Открыть журнал"
@bot.message_handler(func=lambda message: message.text == '📕Посмотреть журнал')
def napare(message):
    if message.chat.id in ADMINS:
        if NA_PARE:
            res = ', '.join(NA_PARE)
            bot.send_message(message.chat.id, res, parse_mode='Markdown')
        else: bot.send_message(message.chat.id, "Никто еще не отметился 😒", parse_mode='Markdown')
    else: bot.send_message(message.chat.id, "Вы не староста!")


# Обработчик нажатия на кнопку "Помощь"
@bot.message_handler(func=lambda message: message.text == '❓ Помощь')
def button_help(message):
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')


# Обработчик нажатия на кнопку "О боте"
@bot.message_handler(func=lambda message: message.text == 'ℹ️ О боте')
def button_about(message):
    bot.send_message(message.chat.id, about_text, parse_mode='Markdown')


@bot.message_handler(func=lambda message: message.text == '📕 Спрятать журнал')
def hide_journal(message):
    if message.from_user.id in ADMINS:
        user_id = message.from_user.id
        global saved_point
        saved_point = None
        user_states[user_id] = None
        bot.send_message(message.chat.id, "Журнал закртыт, жду следующего открытия")
    else: bot.send_message(message.chat.id, "Вы не староста!")

@bot.message_handler(func=lambda message: message.text == '📗 Достать журнал')
def get_journal(message):
    if message.from_user.id in ADMINS:
        user_id = message.from_user.id
        user_states[user_id] = 'waiting_for_point'
        bot.send_message(message.chat.id, "📍 Отправьте точку на карте или вашу геолокацию")
    else: bot.send_message(message.chat.id, "Вы не староста!")



@bot.message_handler(content_types=['location'])
def handle_location(message):
    user_id = message.from_user.id
    global saved_point
    # Проверка для админа - сохранение точки
    if user_id in ADMINS and user_states.get(user_id) == 'waiting_for_point':
        saved_point = {
            'latitude': message.location.latitude,
            'longitude': message.location.longitude,
            'user_id': user_id}
        
        user_states[user_id] = None
        bot.send_message(message.chat.id, f"✅ Точка сохранена: {saved_point['latitude']}, {saved_point['longitude']}")
        return

    # Проверка для студентов - отметка на паре
    if saved_point is None:
        bot.send_message(message.chat.id, "Точка не добавлена, обратитесь к Старосте!")
        return
    
    # Проверяем живую геолокацию
    if hasattr(message.location, 'live_period') and message.location.live_period is not None:
        bot.send_message(message.chat.id, f"✅ Это живая геолокация! Время жизни: {message.location.live_period} секунд")
        
        # Проверяем нахождение в радиусе ПЕРЕДЕЛАТЬ
        if is_in_radius_meters(saved_point['latitude'], saved_point['longitude'], 
                             message.location.latitude, message.location.longitude, RADIUS):
            if str(message.chat.id) not in NA_PARE:
                NA_PARE.append(str(message.chat.id))
                bot.send_message(message.chat.id, "Вы отметились ✅")
            else:
                bot.send_message(message.chat.id, "Вы уже отметились ранее ✅")
        else:
            bot.send_message(message.chat.id, "Вы не на паре ❌")
        return

    # Если не живая геолокация
    bot.send_message(message.chat.id, "❌ Это НЕ живая геолокация! Используйте кнопку '📍 Отправить геолокацию'")

@bot.message_handler(commands=['getpoint'])
def get_point_command(message):
    if saved_point is not None:  # Лучше проверять так
        bot.send_message(message.chat.id, f"📍 Сохраненная точка: {saved_point['latitude']}, {saved_point['longitude']}, ID: {saved_point['user_id']}")
    else:
        bot.send_message(message.chat.id, "❌ Точка не сохранена")





# Обработчик текстовых сообщений
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    # Игнорируем сообщения, которые уже обработаны как нажатия кнопок
    if message.text not in COMMANDS:
        bot.reply_to(message, response_text, parse_mode='Markdown')


if __name__ == '__main__':
    print("🤖 Бот запущен и готов к работе!")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Bot crashed: {e}")