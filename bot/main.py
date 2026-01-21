"""Улучшенная версия Telegram бота с админ-панелью и улучшенным UX"""
import asyncio
import logging
from datetime import date, datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    ConversationHandler, CallbackQueryHandler, filters, ContextTypes
)
from telegram.constants import ParseMode, ChatAction

from config import settings
from database.database import get_db_sync, init_db
from database.models import Client, MatrixCalculation, Feedback
from matrix_calculator import MatrixCalculator, MatrixData
from reports import ReportGenerator
from bot.admin_panel import (
    admin_panel, admin_clients, admin_stats, admin_recent, admin_settings, admin_check
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния разговора
WAITING_NAME, WAITING_DATE, WAITING_GENDER, WAITING_FEEDBACK = range(4)

# Инициализация
calculator = MatrixCalculator()
report_generator = ReportGenerator()


def create_progress_indicator(current: int, total: int) -> str:
    """Создает индикатор прогресса"""
    filled = "█" * current
    empty = "░" * (total - current)
    return f"{filled}{empty} {current}/{total}"


async def send_typing_action(update: Update):
    """Отправляет индикатор печати"""
    await update.message.chat.send_action(ChatAction.TYPING)
    await asyncio.sleep(0.5)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    
    # Проверка на админа
    if await admin_check(update):
        keyboard = [
            [InlineKeyboardButton("🔐 Админ-панель", callback_data="admin_panel")],
            [InlineKeyboardButton("✨ Рассчитать матрицу", callback_data="calculate")],
            [InlineKeyboardButton("📊 История расчетов", callback_data="history")],
            [InlineKeyboardButton("ℹ️ О матрице судьбы", callback_data="info")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("✨ Рассчитать матрицу", callback_data="calculate")],
            [InlineKeyboardButton("📊 История расчетов", callback_data="history")],
            [InlineKeyboardButton("ℹ️ О матрице судьбы", callback_data="info")],
            [InlineKeyboardButton("💬 Помощь", callback_data="help")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🌟 <b>Добро пожаловать, {user.first_name}!</b>

Я помогу вам рассчитать вашу <b>личную матрицу судьбы</b> — уникальную нумерологическую схему, которая раскрывает:

✨ Ваши таланты и способности
🎯 Жизненный путь и предназначение
💫 Кармические задачи
💪 Сильные и слабые стороны
💰 Финансовые возможности

📋 <b>Для расчета понадобятся:</b>
• Ваше полное имя
• Дата рождения
• Пол (опционально)

Выберите действие:
"""
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "calculate":
        await query.edit_message_text(
            f"✨ <b>Расчет матрицы судьбы</b>\n\n"
            f"{create_progress_indicator(1, 3)}\n\n"
            "👤 Пожалуйста, введите ваше <b>полное имя</b> (как в паспорте):\n\n"
            "💡 <i>Пример: Иван Иванов</i>",
            parse_mode=ParseMode.HTML
        )
        return WAITING_NAME
    
    elif query.data == "history":
        await show_history(update, context)
        return ConversationHandler.END
    
    elif query.data == "info":
        info_text = """
📖 <b>О матрице судьбы</b>

Матрица судьбы — это мощная нумерологическая система, которая помогает:

🎯 <b>Понять себя</b>
Раскрыть свои истинные таланты, сильные стороны и области для развития.

🌟 <b>Найти предназначение</b>
Узнать свой жизненный путь и миссию в этом мире.

💫 <b>Работать с кармой</b>
Выявить кармические задачи и уроки, которые нужно пройти.

💰 <b>Улучшить финансы</b>
Понять свои финансовые возможности и препятствия.

💑 <b>Улучшить отношения</b>
Узнать о совместимости и особенностях общения.

<b>Расчет основан на:</b>
• Вашей дате рождения
• Вашем имени

Нажмите /start для начала расчета.
"""
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(info_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    
    elif query.data == "help":
        help_text = """
💬 <b>Помощь</b>

<b>Как использовать бота:</b>

1️⃣ Нажмите "Рассчитать матрицу"
2️⃣ Введите ваше полное имя
3️⃣ Введите дату рождения (ДД.ММ.ГГГГ)
4️⃣ Выберите пол (можно пропустить)
5️⃣ Получите результат!

<b>Команды:</b>
/start - Главное меню
/history - История расчетов
/cancel - Отменить текущую операцию

<b>Вопросы?</b>
Если у вас возникли вопросы, напишите администратору.
"""
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    
    elif query.data == "back_to_main":
        await start_from_callback(update, context)
        return ConversationHandler.END
    
    elif query.data == "admin_panel":
        await admin_panel(update, context)
        return ConversationHandler.END
    
    elif query.data.startswith("admin_"):
        await handle_admin_callback(update, context, query.data)
        return ConversationHandler.END


async def start_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск главного меню из callback"""
    query = update.callback_query
    user = query.from_user
    
    if await admin_check(update):
        keyboard = [
            [InlineKeyboardButton("🔐 Админ-панель", callback_data="admin_panel")],
            [InlineKeyboardButton("✨ Рассчитать матрицу", callback_data="calculate")],
            [InlineKeyboardButton("📊 История расчетов", callback_data="history")],
            [InlineKeyboardButton("ℹ️ О матрице судьбы", callback_data="info")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("✨ Рассчитать матрицу", callback_data="calculate")],
            [InlineKeyboardButton("📊 История расчетов", callback_data="history")],
            [InlineKeyboardButton("ℹ️ О матрице судьбы", callback_data="info")],
            [InlineKeyboardButton("💬 Помощь", callback_data="help")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🌟 <b>Главное меню</b>

Выберите действие:
"""
    
    await query.edit_message_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Обработка админских callback"""
    if data == "admin_panel":
        await admin_panel(update, context)
    elif data == "admin_clients":
        await admin_clients(update, context, 0)
    elif data == "admin_stats":
        await admin_stats(update, context)
    elif data == "admin_recent":
        await admin_recent(update, context)
    elif data == "admin_settings":
        await admin_settings(update, context)
    elif data.startswith("admin_clients_"):
        page = int(data.split("_")[-1])
        await admin_clients(update, context, page)


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение имени с улучшенной валидацией"""
    name = update.message.text.strip()
    
    # Валидация
    if len(name) < 2:
        await update.message.reply_text(
            "❌ Имя слишком короткое. Пожалуйста, введите полное имя (минимум 2 символа):"
        )
        return WAITING_NAME
    
    if len(name) > 100:
        await update.message.reply_text(
            "❌ Имя слишком длинное. Пожалуйста, введите корректное имя:"
        )
        return WAITING_NAME
    
    # Проверка на недопустимые символы
    if any(char.isdigit() for char in name):
        await update.message.reply_text(
            "❌ Имя не должно содержать цифры. Пожалуйста, введите корректное имя:"
        )
        return WAITING_NAME
    
    context.user_data['name'] = name
    
    await update.message.reply_text(
        f"✅ Имя сохранено: <b>{name}</b>\n\n"
        f"{create_progress_indicator(2, 3)}\n\n"
        "📅 Теперь введите <b>дату рождения</b> в формате <b>ДД.ММ.ГГГГ</b>\n\n"
        "💡 <i>Пример: 15.03.1990</i>",
        parse_mode=ParseMode.HTML
    )
    return WAITING_DATE


async def receive_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение даты рождения с улучшенной валидацией"""
    date_str = update.message.text.strip()
    
    try:
        # Поддержка разных форматов
        date_str = date_str.replace('/', '.').replace('-', '.').replace(' ', '')
        
        parts = date_str.split('.')
        if len(parts) != 3:
            raise ValueError("Неверный формат")
        
        day, month, year = map(int, parts)
        birth_date = date(year, month, day)
        
        # Проверка на разумность даты
        if birth_date > date.today():
            await update.message.reply_text(
                "❌ Дата рождения не может быть в будущем. Попробуйте еще раз:"
            )
            return WAITING_DATE
        
        if year < 1900:
            await update.message.reply_text(
                "❌ Год рождения должен быть не ранее 1900. Попробуйте еще раз:"
            )
            return WAITING_DATE
        
        # Проверка возраста
        age = (date.today() - birth_date).days // 365
        if age > 120:
            await update.message.reply_text(
                "❌ Пожалуйста, проверьте правильность даты рождения:"
            )
            return WAITING_DATE
        
        context.user_data['birth_date'] = birth_date
        
        keyboard = [
            [
                InlineKeyboardButton("👨 Мужской", callback_data="gender_male"),
                InlineKeyboardButton("👩 Женский", callback_data="gender_female")
            ],
            [InlineKeyboardButton("⏭️ Пропустить", callback_data="gender_skip")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Дата сохранена: <b>{birth_date.strftime('%d.%m.%Y')}</b>\n\n"
            f"{create_progress_indicator(3, 3)}\n\n"
            "👤 Выберите ваш <b>пол</b> (можно пропустить):",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return WAITING_GENDER
        
    except (ValueError, AttributeError) as e:
        await update.message.reply_text(
            "❌ Неверный формат даты. Используйте формат <b>ДД.ММ.ГГГГ</b>\n\n"
            "💡 <i>Пример: 15.03.1990</i>",
            parse_mode=ParseMode.HTML
        )
        return WAITING_DATE


async def receive_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение пола через кнопку"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "gender_skip":
        context.user_data['gender'] = None
    else:
        gender_map = {"gender_male": "male", "gender_female": "female"}
        context.user_data['gender'] = gender_map.get(query.data)
    
    # Выполняем расчет
    await calculate_matrix(update, context)
    return ConversationHandler.END


async def calculate_matrix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выполнение расчета матрицы с улучшенным UX"""
    if isinstance(update, Update) and update.callback_query:
        query = update.callback_query
        message = query.message
    else:
        message = update.message
    
    # Получаем данные
    name = context.user_data.get('name')
    birth_date = context.user_data.get('birth_date')
    gender = context.user_data.get('gender')
    
    if not name or not birth_date:
        await message.reply_text("❌ Ошибка: не все данные получены. Начните заново: /start")
        return
    
    # Показываем процесс с индикатором
    processing_msg = await message.reply_text(
        "⏳ <b>Выполняю расчет матрицы...</b>\n\n"
        "🔮 Анализирую ваши данные...",
        parse_mode=ParseMode.HTML
    )
    
    # Имитация процесса для лучшего UX
    await asyncio.sleep(0.5)
    await processing_msg.edit_text(
        "⏳ <b>Выполняю расчет матрицы...</b>\n\n"
        "📊 Рассчитываю числа судьбы...",
        parse_mode=ParseMode.HTML
    )
    
    try:
        # Создаем данные для расчета
        matrix_data = MatrixData(
            birth_date=birth_date,
            name=name,
            gender=gender
        )
        
        # Выполняем расчет
        result = calculator.calculate_matrix(matrix_data)
        
        await processing_msg.edit_text(
            "⏳ <b>Выполняю расчет матрицы...</b>\n\n"
            "✨ Формирую интерпретации...",
            parse_mode=ParseMode.HTML
        )
        
        # Генерируем отчет
        text_report = report_generator.generate_text_report(matrix_data, result)
        visual_matrix = report_generator.generate_visual_matrix(result)
        
        # Сохраняем в базу данных
        await save_calculation(update, context, matrix_data, result)
        
        # Отправляем результаты
        await processing_msg.delete()
        
        # Отправляем визуализацию
        await message.reply_photo(
            photo=visual_matrix,
            caption=f"🎯 <b>Ваша матрица судьбы</b>\n\n"
                   f"👤 {name}\n"
                   f"📅 {birth_date.strftime('%d.%m.%Y')}",
            parse_mode=ParseMode.HTML
        )
        
        # Отправляем текстовый отчет частями
        max_length = 4000
        if len(text_report) > max_length:
            parts = [text_report[i:i+max_length] for i in range(0, len(text_report), max_length)]
            for i, part in enumerate(parts, 1):
                await message.reply_text(
                    f"<pre>{part}</pre>",
                    parse_mode=ParseMode.HTML
                )
        else:
            await message.reply_text(
                f"<pre>{text_report}</pre>",
                parse_mode=ParseMode.HTML
            )
        
        # Кнопки для дополнительных действий
        keyboard = [
            [InlineKeyboardButton("⭐ Оценить расчет", callback_data="feedback")],
            [
                InlineKeyboardButton("🔄 Новый расчет", callback_data="calculate"),
                InlineKeyboardButton("📊 История", callback_data="history")
            ],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(
            "✅ <b>Расчет завершен!</b>\n\n"
            "Выберите действие:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Ошибка при расчете: {e}", exc_info=True)
        await processing_msg.edit_text(
            f"❌ Произошла ошибка при расчете.\n\n"
            f"Попробуйте еще раз: /start\n\n"
            f"Если ошибка повторяется, обратитесь к администратору."
        )


async def save_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                          matrix_data: MatrixData, result):
    """Сохраняет расчет в базу данных"""
    try:
        user_id = str(update.effective_user.id)
        db = get_db_sync()
        
        try:
            # Находим или создаем клиента
            client = db.query(Client).filter(Client.telegram_id == user_id).first()
            if not client:
                client = Client(
                    telegram_id=user_id,
                    name=matrix_data.name,
                    birth_date=matrix_data.birth_date,
                    gender=matrix_data.gender
                )
                db.add(client)
                db.commit()
                db.refresh(client)
            
            # Сохраняем расчет
            calculation = MatrixCalculation(
                client_id=client.id,
                result_data=result.model_dump()
            )
            db.add(calculation)
            db.commit()
        finally:
            db.close()
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении: {e}")


async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает историю расчетов с пагинацией"""
    try:
        user_id = str(update.effective_user.id)
        db = get_db_sync()
        
        try:
            client = db.query(Client).filter(Client.telegram_id == user_id).first()
            
            if not client or not client.calculations:
                text = "📊 У вас пока нет сохраненных расчетов.\n\nНачните новый расчет: /start"
                if update.callback_query:
                    await update.callback_query.edit_message_text(text)
                else:
                    await update.message.reply_text(text)
                return
            
            text = f"📊 <b>История расчетов</b>\n\n"
            text += f"Всего расчетов: <b>{len(client.calculations)}</b>\n\n"
            
            # Показываем последние 10
            for i, calc in enumerate(client.calculations[-10:], 1):
                date_str = calc.created_at.strftime("%d.%m.%Y %H:%M")
                text += f"{i}. {date_str}\n"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Новый расчет", callback_data="calculate")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
                )
            else:
                await update.message.reply_text(
                    text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
                )
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Ошибка при показе истории: {e}")


async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка обратной связи"""
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for i in range(1, 6):
        keyboard.append([InlineKeyboardButton("⭐" * i, callback_data=f"rating_{i}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⭐ <b>Оцените расчет</b>\n\n"
        "Насколько полезным был расчет матрицы?\n"
        "Выберите оценку от 1 до 5 звезд:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )


async def receive_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получение оценки"""
    query = update.callback_query
    await query.answer()
    
    rating = int(query.data.split("_")[1])
    
    # Сохраняем оценку
    try:
        user_id = str(update.effective_user.id)
        db = get_db_sync()
        
        try:
            client = db.query(Client).filter(Client.telegram_id == user_id).first()
            if client:
                # Получаем последний расчет
                last_calc = db.query(MatrixCalculation).filter(
                    MatrixCalculation.client_id == client.id
                ).order_by(MatrixCalculation.created_at.desc()).first()
                
                feedback = Feedback(
                    client_id=client.id,
                    calculation_id=last_calc.id if last_calc else None,
                    rating=rating
                )
                db.add(feedback)
                db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Ошибка при сохранении оценки: {e}")
    
    await query.edit_message_text(
        f"⭐ <b>Спасибо за оценку!</b>\n\n"
        f"Вы оценили расчет на <b>{rating}</b> {'звезд' if rating > 1 else 'звезду'}.\n\n"
        f"Ваше мнение помогает нам становиться лучше! 🙏",
        parse_mode=ParseMode.HTML
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена операции"""
    await update.message.reply_text(
        "❌ Операция отменена. Для начала нового расчета используйте /start"
    )
    return ConversationHandler.END


def main():
    """Главная функция запуска бота"""
    # Инициализация базы данных
    init_db()
    
    # Создание приложения
    application = Application.builder().token(settings.telegram_bot_token).build()
    
    # Обработчик разговора для расчета
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^calculate$")],
        states={
            WAITING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            WAITING_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_date)],
            WAITING_GENDER: [CallbackQueryHandler(receive_gender)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CallbackQueryHandler(handle_feedback, pattern="^feedback$"))
    application.add_handler(CallbackQueryHandler(receive_rating, pattern="^rating_"))
    application.add_handler(CommandHandler("admin", admin_panel))
    
    # Запуск бота
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
