import telebot
from telebot import types
from settings import BOT_TOKEN, ADMINS, COMMANDS, user_states, RADIUS, saved_point
from messages import welcome_text, about_text, help_text, response_text, location_text, registration_notice
from geopos import is_in_radius_meters
from db_init import StudentDB
import datetime

db = StudentDB()

bot = telebot.TeleBot(BOT_TOKEN)

def is_registered(user_id):
    """Проверяет, зарегистрирован ли пользователь"""
    return db.get_student(str(user_id)) is not None

def get_keyboard(chat_id):
    """Возвращает клавиатуру в зависимости от статуса пользователя"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    
    # Базовые кнопки для всех
    btn_help = types.KeyboardButton('❓ Помощь')
    btn_about = types.KeyboardButton('ℹ️ О боте')
    
    # Если пользователь не зарегистрирован - только 3 кнопки
    if not is_registered(chat_id):
        btn_register = types.KeyboardButton('👤 Зарегистрироваться')
        markup.add(btn_help, btn_about, btn_register)
        return markup
    
    # Если пользователь зарегистрирован - добавляем функциональные кнопки
    btn_online = types.KeyboardButton('🧾 Отметиться на паре')
    markup.add(btn_help, btn_about, btn_online)
    
    # Кнопки для админов
    if chat_id in ADMINS:
        btn_list = types.KeyboardButton('📕 Посмотреть журнал')
        btn_openjournal = types.KeyboardButton('📗 Достать журнал')
        btn_closejournal = types.KeyboardButton('📕 Спрятать журнал')
        markup.add(btn_openjournal, btn_closejournal, btn_list)
    
    return markup

# Обработчик регистрации
@bot.message_handler(func=lambda message: message.text == '👤 Зарегистрироваться')
def register_user(message):
    user_id = str(message.from_user.id)
    
    # Проверяем, есть ли уже студент в базе
    if is_registered(user_id):
        bot.send_message(message.chat.id, "Вы уже зарегистрированы! ✅")
        return
    
    user_states[user_id] = 'waiting_for_name'
    bot.send_message(message.chat.id, 
                    "📝 *Регистрация студента*\n\n"
                    "Введите ваше *Имя и Фамилию* через пробел:\n"
                    "Например: *Иван Иванов*", 
                    parse_mode='Markdown')

@bot.message_handler(func=lambda message: user_states.get(str(message.from_user.id)) == 'waiting_for_name')
def process_name(message):
    user_id = str(message.from_user.id)
    full_name = message.text.strip()
    
    # Валидация имени и фамилии
    name_parts = full_name.split()
    if len(name_parts) < 2:
        bot.send_message(message.chat.id, 
                        "❌ Пожалуйста, введите *Имя и Фамилию* через пробел:\n"
                        "Например: *Иван Иванов*", 
                        parse_mode='Markdown')
        return
    
    # Сохраняем имя и переходим к вводу группы
    user_states[user_id] = 'waiting_for_group'
    user_states[f'{user_id}_name'] = full_name  # Временно сохраняем имя
    
    bot.send_message(message.chat.id,
                    "✅ Имя сохранено!\n\n"
                    "Теперь введите вашу *группу*:\n"
                    "Например: *ИТ-21* или *КБ-31*",
                    parse_mode='Markdown')

@bot.message_handler(func=lambda message: user_states.get(str(message.from_user.id)) == 'waiting_for_group')
def process_group(message):
    user_id = str(message.from_user.id)
    group_name = message.text.strip()
    
    # Валидация группы
    if len(group_name) < 2:
        bot.send_message(message.chat.id, 
                        "❌ Пожалуйста, введите корректное название группы:\n"
                        "Например: *ИТ-21* или *КБ-31*", 
                        parse_mode='Markdown')
        return
    
    # Получаем сохраненное имя
    full_name = user_states.get(f'{user_id}_name')
    
    # Очищаем состояния
    user_states[user_id] = None
    if f'{user_id}_name' in user_states:
        del user_states[f'{user_id}_name']
    
    # Сохраняем в базу данных
    if db.add_student(user_id, full_name, group_name):
        # Обновляем клавиатуру после регистрации
        markup = get_keyboard(message.chat.id)
        bot.send_message(message.chat.id,
                        f"✅ *Регистрация успешна!*\n\n"
                        f"👤 *Студент:* {full_name}\n"
                        f"👥 *Группа:* {group_name}\n\n"
                        f"Теперь вы можете отмечаться на парах!",
                        reply_markup=markup,
                        parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, 
                        "❌ Ошибка регистрации. Возможно, вы уже зарегистрированы.")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    try:
        user_name = message.from_user.first_name
        user_id = str(message.chat.id)

        print("Пользователь", user_name, "с айди", message.chat.id, "запустил бота")
        
        # Получаем актуальную клавиатуру
        markup = get_keyboard(message.chat.id)
        
        # Форматируем приветственное сообщение
        if is_registered(user_id):
            welcome_msg = welcome_text.format(user_name) + "\n\n✅ *Вы зарегистрированы*"
        else:
            welcome_msg = welcome_text.format(user_name) + "\n\n" + registration_notice

        bot.send_message(message.chat.id, welcome_msg, reply_markup=markup, parse_mode='Markdown')
        
    except Exception as e:
        print(f"Error in send_welcome: {e}")

@bot.message_handler(commands=['about'])
def send_about(message):
    bot.reply_to(message, about_text)

@bot.message_handler(func=lambda message: message.text == '📕 Посмотреть журнал')
def show_journal(message):
    if not is_registered(message.chat.id):
        bot.send_message(message.chat.id, "❌ Сначала зарегистрируйтесь!")
        return
        
    if message.chat.id in ADMINS:
        # Получаем всех студентов и тех, кто на паре
        all_students = db.get_all_students()
        current_attendance = db.get_current_attendance()
        current_user_ids = [student['user_id'] for student in current_attendance]
        
        if not all_students:
            bot.send_message(message.chat.id, "❌ Нет зарегистрированных студентов")
            return
        
        # Группируем по группам
        groups = {}
        for student in all_students:
            group = student['group_name']
            if group not in groups:
                groups[group] = []
            groups[group].append(student)
        
        journal_text = "📖 *Журнал посещений*\n\n"
        
        for group_name, students in sorted(groups.items()):
            journal_text += f"👥 *{group_name}:*\n"
            
            for student in sorted(students, key=lambda x: x['full_name']):
                status = "✅" if student['user_id'] in current_user_ids else "❌"
                journal_text += f"   {status} {student['full_name']}\n"
            
            # Статистика по группе
            group_present = sum(1 for s in students if s['user_id'] in current_user_ids)
            group_total = len(students)
            
            journal_text += f"   📊 {group_present}/{group_total}\n\n"
        
        # Общая статистика
        present_count = len(current_attendance)
        total_count = len(all_students)
        
        journal_text += f"📋 *Всего отметилось:* {present_count}/{total_count}"
        
        bot.send_message(message.chat.id, journal_text, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Вы не староста!")

@bot.message_handler(func=lambda message: message.text == '🧾 Отметиться на паре')
def otmetica(message):
    user_id = str(message.chat.id)
    
    # Проверяем регистрацию
    if not is_registered(user_id):
        bot.send_message(message.chat.id, "❌ Сначала зарегистрируйтесь с помощью кнопки '👤 Зарегистрироваться'")
        return
    
    # Проверяем, не отметился ли уже
    current_attendance = db.get_current_attendance()
    current_user_ids = [student['user_id'] for student in current_attendance]
    
    if user_id in current_user_ids:
        bot.send_message(message.chat.id, "Вы уже отметились ✅")
    else:
        bot.send_message(message.chat.id, location_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '❓ Помощь')
def button_help(message):
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == 'ℹ️ О боте')
def button_about(message):
    bot.send_message(message.chat.id, about_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.text == '📕 Спрятать журнал')
def hide_journal(message):
    if not is_registered(message.chat.id):
        bot.send_message(message.chat.id, "❌ Сначала зарегистрируйтесь!")
        return
        
    if message.from_user.id in ADMINS:
        if db.clear_current_class():
            bot.send_message(message.chat.id, "✅ Журнал очищен, все студенты удалены из текущей пары")
        else:
            bot.send_message(message.chat.id, "❌ Ошибка при очистке журнала")
    else:
        bot.send_message(message.chat.id, "❌ Вы не староста!")

@bot.message_handler(func=lambda message: message.text == '📗 Достать журнал')
def get_journal(message):
    if not is_registered(message.chat.id):
        bot.send_message(message.chat.id, "❌ Сначала зарегистрируйтесь!")
        return
        
    if message.from_user.id in ADMINS:
        user_id = str(message.from_user.id)
        user_states[user_id] = 'waiting_for_point'
        bot.send_message(message.chat.id, "📍 Отправьте точку на карте или вашу геолокацию")
    else:
        bot.send_message(message.chat.id, "❌ Вы не староста!")

@bot.message_handler(content_types=['location'])
def handle_location(message):
    user_id = str(message.chat.id)
    global saved_point

    # Проверка для админа - сохранение точки
    if message.from_user.id in ADMINS and user_states.get(user_id) == 'waiting_for_point':
        saved_point = {
            'latitude': message.location.latitude,
            'longitude': message.location.longitude,
            'user_id': user_id
        }
        
        user_states[user_id] = None
        bot.send_message(message.chat.id, f"✅ Точка сохранена: {saved_point['latitude']}, {saved_point['longitude']}")
        return

    # Проверка регистрации для студентов
    if not is_registered(user_id):
        bot.send_message(message.chat.id, "❌ Сначала зарегистрируйтесь с помощью кнопки '👤 Зарегистрироваться'")
        return

    # Проверка для студентов - отметка на паре
    if saved_point is None:
        bot.send_message(message.chat.id, "📍 Точка для отметки не установлена. Обратитесь к старосте!")
        return

    # Проверяем, не отметился ли уже студент на текущей паре
    current_attendance = db.get_current_attendance()
    current_user_ids = [student['user_id'] for student in current_attendance]
    
    if user_id in current_user_ids:
        bot.send_message(message.chat.id, "✅ Вы уже отметились на этой паре")
        return

    # Проверяем живую геолокацию
    is_live_location = hasattr(message.location, 'live_period') and message.location.live_period is not None
    
    if not is_live_location:
        bot.send_message(message.chat.id, "❌ Это НЕ живая геолокация! Используйте кнопку '📍 Отправить геолокацию'")
        return

    # Проверяем нахождение в радиусе
    in_radius = is_in_radius_meters(
        saved_point['latitude'], 
        saved_point['longitude'], 
        message.location.latitude, 
        message.location.longitude, 
        RADIUS
    )

    if in_radius:
        # Отмечаем студента в базе данных
        if db.mark_attendance(user_id):
            student = db.get_student(user_id)
            student_name = student['full_name']
            response_text = f"✅ {student_name}, вы успешно отметились на паре!"
            
            bot.send_message(message.chat.id, response_text)
            
            # Уведомляем админов о новой отметке
            for admin_id in ADMINS:
                try:
                    bot.send_message(
                        admin_id, 
                        f"🎯 Новый студент отметился:\n"
                        f"• {student_name}\n"
                        f"• Время: {datetime.datetime.now().strftime('%H:%M:%S')}"
                    )
                except Exception as e:
                    print(f"Не удалось отправить уведомление админу {admin_id}: {e}")
        else:
            bot.send_message(message.chat.id, "❌ Ошибка при сохранении отметки. Попробуйте еще раз.")
    else:
        bot.send_message(message.chat.id, "❌ Вы не на паре! Находитесь слишком далеко от точки отметки.")

@bot.message_handler(commands=['getpoint'])
def get_point_command(message):
    if not is_registered(message.chat.id):
        bot.send_message(message.chat.id, "❌ Сначала зарегистрируйтесь!")
        return
        
    if saved_point is not None:
        bot.send_message(message.chat.id, f"📍 Сохраненная точка: {saved_point['latitude']}, {saved_point['longitude']}")
    else:
        bot.send_message(message.chat.id, "❌ Точка не сохранена")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    # Проверяем регистрацию для всех остальных команд
    if not is_registered(message.chat.id) and message.text not in ['❓ Помощь', 'ℹ️ О боте', '👤 Зарегистрироваться']:
        bot.send_message(message.chat.id, "❌ Сначала зарегистрируйтесь с помощью кнопки '👤 Зарегистрироваться'")
        return
        
    if message.text not in COMMANDS:
        bot.reply_to(message, response_text, parse_mode='Markdown')

if __name__ == '__main__':
    print("🤖 Бот запущен и готов к работе!")
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Bot crashed: {e}")