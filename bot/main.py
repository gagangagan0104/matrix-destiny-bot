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
    percentage = int((current / total) * 100)
    return f"<code>{filled}{empty}</code> <b>{percentage}%</b> ({current}/{total})"


def create_section_header(title: str, emoji: str = "✨") -> str:
    """Создает заголовок секции"""
    return f"\n{emoji} <b>{title}</b>\n{'─' * 30}\n"


def format_key_number(number: int, label: str) -> str:
    """Форматирует ключевое число"""
    return f"<b>🔢 {label}:</b> <code>{number}</code>"


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
            [InlineKeyboardButton("✨ Рассчитать матрицу", callback_data="calculate")],
            [
                InlineKeyboardButton("📊 История", callback_data="history"),
                InlineKeyboardButton("ℹ️ О матрице", callback_data="info")
            ],
            [InlineKeyboardButton("🔐 Админ-панель", callback_data="admin_panel")]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("✨ Рассчитать матрицу", callback_data="calculate")],
            [
                InlineKeyboardButton("📊 История расчетов", callback_data="history"),
                InlineKeyboardButton("ℹ️ О матрице", callback_data="info")
            ],
            [InlineKeyboardButton("💬 Помощь", callback_data="help")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
╔═══════════════════════════════════╗
║   🔮 ЛИЧНАЯ МАТРИЦА СУДЬБЫ 🔮    ║
╚═══════════════════════════════════╝

👋 <b>Добро пожаловать, {user.first_name}!</b>

Я помогу вам раскрыть тайны вашей судьбы через <b>нумерологический анализ</b> вашей личности.

{create_section_header("Что вы узнаете", "✨")}
🎯 <b>Ваш жизненный путь</b> и предназначение
💫 <b>Кармические задачи</b> и уроки
💪 <b>Сильные стороны</b> и таланты
💰 <b>Финансовые возможности</b>
💑 <b>Совместимость</b> в отношениях

{create_section_header("Для расчета нужно", "📋")}
• Полное имя (как в паспорте)
• Дата рождения (ДД.ММ.ГГГГ)
• Пол (опционально)

<b>⏱️ Расчет займет всего 30 секунд!</b>
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
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✨ <b>РАСЧЕТ МАТРИЦЫ СУДЬБЫ</b>\n\n"
            f"{create_progress_indicator(1, 3)}\n\n"
            f"{create_section_header('Шаг 1 из 3: Введите имя', '👤')}"
            "Пожалуйста, введите ваше <b>полное имя</b> (как в паспорте):\n\n"
            "💡 <i>Пример: Иван Иванов</i>\n"
            "💡 <i>Или: Мария Петрова</i>",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return WAITING_NAME
    
    elif query.data == "history":
        await show_history(update, context)
        return ConversationHandler.END
    
    elif query.data == "info":
        info_text = f"""
╔═══════════════════════════════════╗
║   📖 О МАТРИЦЕ СУДЬБЫ            ║
╚═══════════════════════════════════╝

Матрица судьбы — это <b>мощная нумерологическая система</b>, основанная на древних знаниях, которая помогает раскрыть тайны вашей личности.

{create_section_header("Что дает матрица", "🎯")}
<b>🔍 Понять себя</b>
Раскрыть свои истинные таланты, сильные стороны и области для развития.

<b>🌟 Найти предназначение</b>
Узнать свой жизненный путь и миссию в этом мире.

<b>💫 Работать с кармой</b>
Выявить кармические задачи и уроки, которые нужно пройти.

<b>💰 Улучшить финансы</b>
Понять свои финансовые возможности и препятствия.

<b>💑 Улучшить отношения</b>
Узнать о совместимости и особенностях общения.

{create_section_header("Как это работает", "🔮")}
Расчет основан на:
• <b>Вашей дате рождения</b> — определяет жизненный путь
• <b>Вашем имени</b> — раскрывает личность и таланты

Алгоритм анализирует числовые значения и создает <b>уникальную матрицу</b>, которая является вашим персональным ключом к пониманию себя.

<b>✨ Начните свой путь к самопознанию прямо сейчас!</b>
"""
        keyboard = [
            [InlineKeyboardButton("✨ Рассчитать матрицу", callback_data="calculate")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(info_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    
    elif query.data == "help":
        help_text = f"""
╔═══════════════════════════════════╗
║   💬 ПОМОЩЬ И ИНСТРУКЦИИ         ║
╚═══════════════════════════════════╝

{create_section_header("Как использовать бота", "📱")}
<b>1️⃣</b> Нажмите <b>"✨ Рассчитать матрицу"</b>
<b>2️⃣</b> Введите ваше <b>полное имя</b> (как в паспорте)
<b>3️⃣</b> Введите <b>дату рождения</b> в формате ДД.ММ.ГГГГ
<b>4️⃣</b> Выберите <b>пол</b> (можно пропустить)
<b>5️⃣</b> Получите <b>детальный отчет</b>!

{create_section_header("Доступные команды", "⌨️")}
<code>/start</code> — Главное меню
<code>/history</code> — История ваших расчетов
<code>/cancel</code> — Отменить текущую операцию

{create_section_header("Формат даты", "📅")}
Используйте формат: <b>ДД.ММ.ГГГГ</b>
<i>Примеры:</i>
• <code>15.03.1990</code>
• <code>01.12.2000</code>
• <code>25.07.1985</code>

{create_section_header("Нужна помощь?", "❓")}
Если у вас возникли вопросы или проблемы, обратитесь к администратору через команду <code>/start</code>
"""
        keyboard = [
            [InlineKeyboardButton("✨ Рассчитать матрицу", callback_data="calculate")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
        ]
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
╔═══════════════════════════════════╗
║   🏠 ГЛАВНОЕ МЕНЮ                ║
╚═══════════════════════════════════╝

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
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "╔═══════════════════════════════════╗\n"
            "║   ⚠️ ОШИБКА ВВОДА               ║\n"
            "╚═══════════════════════════════════╝\n\n"
            "❌ <b>Имя слишком короткое</b>\n\n"
            "Пожалуйста, введите ваше <b>полное имя</b> (минимум 2 символа).\n\n"
            "💡 <i>Пример: Иван Иванов</i>",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return WAITING_NAME
    
    if len(name) > 100:
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "╔═══════════════════════════════════╗\n"
            "║   ⚠️ ОШИБКА ВВОДА               ║\n"
            "╚═══════════════════════════════════╝\n\n"
            "❌ <b>Имя слишком длинное</b>\n\n"
            "Пожалуйста, введите корректное имя (максимум 100 символов).\n\n"
            "💡 <i>Пример: Иван Иванов</i>",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return WAITING_NAME
    
    # Проверка на недопустимые символы
    if any(char.isdigit() for char in name):
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "╔═══════════════════════════════════╗\n"
            "║   ⚠️ ОШИБКА ВВОДА               ║\n"
            "╚═══════════════════════════════════╝\n\n"
            "❌ <b>Имя не должно содержать цифры</b>\n\n"
            "Пожалуйста, введите ваше имя <b>только буквами</b>.\n\n"
            "💡 <i>Пример: Иван Иванов</i>",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return WAITING_NAME
    
    context.user_data['name'] = name
    
    keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ <b>Имя сохранено!</b>\n\n"
        f"👤 <b>{name}</b>\n\n"
        f"{create_progress_indicator(2, 3)}\n\n"
        f"{create_section_header('Шаг 2 из 3: Введите дату рождения', '📅')}"
        "Пожалуйста, введите <b>дату рождения</b> в формате <b>ДД.ММ.ГГГГ</b>\n\n"
        "💡 <i>Примеры:</i>\n"
        "• <code>15.03.1990</code>\n"
        "• <code>01.12.2000</code>\n"
        "• <code>25.07.1985</code>",
        reply_markup=reply_markup,
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
            keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "╔═══════════════════════════════════╗\n"
                "║   ⚠️ ОШИБКА ВВОДА               ║\n"
                "╚═══════════════════════════════════╝\n\n"
                "❌ <b>Дата рождения не может быть в будущем</b>\n\n"
                "Пожалуйста, введите корректную дату рождения.\n\n"
                "💡 <i>Формат: ДД.ММ.ГГГГ</i>\n"
                "💡 <i>Пример: 15.03.1990</i>",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            return WAITING_DATE
        
        if year < 1900:
            keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "╔═══════════════════════════════════╗\n"
                "║   ⚠️ ОШИБКА ВВОДА               ║\n"
                "╚═══════════════════════════════════╝\n\n"
                "❌ <b>Год рождения должен быть не ранее 1900</b>\n\n"
                "Пожалуйста, введите корректную дату рождения.\n\n"
                "💡 <i>Формат: ДД.ММ.ГГГГ</i>\n"
                "💡 <i>Пример: 15.03.1990</i>",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            return WAITING_DATE
        
        # Проверка возраста
        age = (date.today() - birth_date).days // 365
        if age > 120:
            keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "╔═══════════════════════════════════╗\n"
                "║   ⚠️ ОШИБКА ВВОДА               ║\n"
                "╚═══════════════════════════════════╝\n\n"
                "❌ <b>Пожалуйста, проверьте правильность даты рождения</b>\n\n"
                "Возраст не может превышать 120 лет.\n\n"
                "💡 <i>Формат: ДД.ММ.ГГГГ</i>\n"
                "💡 <i>Пример: 15.03.1990</i>",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
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
            f"✅ <b>Дата сохранена!</b>\n\n"
            f"📅 <b>{birth_date.strftime('%d.%m.%Y')}</b>\n\n"
            f"{create_progress_indicator(3, 3)}\n\n"
            f"{create_section_header('Шаг 3 из 3: Выберите пол', '👤')}"
            "Выберите ваш <b>пол</b> для более точного расчета:\n\n"
            "💡 <i>Этот шаг можно пропустить</i>",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return WAITING_GENDER
        
    except (ValueError, AttributeError) as e:
        keyboard = [[InlineKeyboardButton("🔙 Отмена", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "╔═══════════════════════════════════╗\n"
            "║   ⚠️ ОШИБКА ВВОДА               ║\n"
            "╚═══════════════════════════════════╝\n\n"
            "❌ <b>Неверный формат даты</b>\n\n"
            "Пожалуйста, используйте формат <b>ДД.ММ.ГГГГ</b>\n\n"
            "💡 <i>Примеры:</i>\n"
            "• <code>15.03.1990</code>\n"
            "• <code>01.12.2000</code>\n"
            "• <code>25.07.1985</code>\n\n"
            "<i>Также можно использовать:</i>\n"
            "• <code>15/03/1990</code>\n"
            "• <code>15-03-1990</code>",
            reply_markup=reply_markup,
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
        keyboard = [
            [InlineKeyboardButton("✨ Начать заново", callback_data="calculate")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await message.reply_text(
            "╔═══════════════════════════════════╗\n"
            "║   ⚠️ ОШИБКА ДАННЫХ              ║\n"
            "╚═══════════════════════════════════╝\n\n"
            "❌ <b>Не все данные получены</b>\n\n"
            "Пожалуйста, начните расчет заново.",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return
    
    # Показываем процесс с индикатором
    processing_msg = await message.reply_text(
        "╔═══════════════════════════════════╗\n"
        "║   ⏳ РАСЧЕТ МАТРИЦЫ СУДЬБЫ       ║\n"
        "╚═══════════════════════════════════╝\n\n"
        "🔮 <b>Анализирую ваши данные...</b>\n"
        "<code>░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░</code> <b>0%</b>",
        parse_mode=ParseMode.HTML
    )
    
    # Имитация процесса для лучшего UX
    await asyncio.sleep(0.6)
    await processing_msg.edit_text(
        "╔═══════════════════════════════════╗\n"
        "║   ⏳ РАСЧЕТ МАТРИЦЫ СУДЬБЫ       ║\n"
        "╚═══════════════════════════════════╝\n\n"
        "📊 <b>Рассчитываю числа судьбы...</b>\n"
        "<code>████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░</code> <b>25%</b>",
        parse_mode=ParseMode.HTML
    )
    
    await asyncio.sleep(0.5)
    await processing_msg.edit_text(
        "╔═══════════════════════════════════╗\n"
        "║   ⏳ РАСЧЕТ МАТРИЦЫ СУДЬБЫ       ║\n"
        "╚═══════════════════════════════════╝\n\n"
        "🔢 <b>Формирую матрицу...</b>\n"
        "<code>████████████████░░░░░░░░░░░░░░░░░░░░</code> <b>50%</b>",
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
        
        await asyncio.sleep(0.5)
        await processing_msg.edit_text(
            "╔═══════════════════════════════════╗\n"
            "║   ⏳ РАСЧЕТ МАТРИЦЫ СУДЬБЫ       ║\n"
            "╚═══════════════════════════════════╝\n\n"
            "✨ <b>Формирую интерпретации...</b>\n"
            "<code>████████████████████████░░░░░░░░░░░░</code> <b>75%</b>",
            parse_mode=ParseMode.HTML
        )
        
        await asyncio.sleep(0.4)
        await processing_msg.edit_text(
            "╔═══════════════════════════════════╗\n"
            "║   ⏳ РАСЧЕТ МАТРИЦЫ СУДЬБЫ       ║\n"
            "╚═══════════════════════════════════╝\n\n"
            "🌐 <b>Собираю дополнительную информацию...</b>\n"
            "<code>████████████████████████████░░░░░░░░</code> <b>80%</b>",
            parse_mode=ParseMode.HTML
        )
        
        # Генерируем расширенный отчет с информацией с сайтов
        enhanced_report = await report_generator.generate_enhanced_report(matrix_data, result)
        text_report = enhanced_report['text_report']
        visual_matrix = enhanced_report['visual_matrix']
        additional_images = enhanced_report.get('additional_images', [])
        
        await asyncio.sleep(0.3)
        await processing_msg.edit_text(
            "╔═══════════════════════════════════╗\n"
            "║   ⏳ РАСЧЕТ МАТРИЦЫ СУДЬБЫ       ║\n"
            "╚═══════════════════════════════════╝\n\n"
            "🎯 <b>Завершаю расчет...</b>\n"
            "<code>████████████████████████████████████</code> <b>100%</b>",
            parse_mode=ParseMode.HTML
        )
        
        # Сохраняем в базу данных
        await save_calculation(update, context, matrix_data, result)
        
        # Отправляем результаты
        await processing_msg.delete()
        
        # Отправляем визуализацию матрицы
        await message.reply_photo(
            photo=visual_matrix,
            caption=f"╔═══════════════════════════════════╗\n"
                   f"║   🎯 ВАША МАТРИЦА СУДЬБЫ          ║\n"
                   f"╚═══════════════════════════════════╝\n\n"
                   f"👤 <b>{name}</b>\n"
                   f"📅 <b>{birth_date.strftime('%d.%m.%Y')}</b>\n\n"
                   f"✨ <i>Ваша уникальная матрица готова!</i>",
            parse_mode=ParseMode.HTML
        )
        
        # Отправляем дополнительные изображения, если есть
        for img_bytes in additional_images[:2]:  # Максимум 2 дополнительных изображения
            try:
                await message.reply_photo(photo=img_bytes)
            except Exception as e:
                logger.error(f"Ошибка при отправке дополнительного изображения: {e}")
        
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
            "╔═══════════════════════════════════╗\n"
            "║   ✅ РАСЧЕТ ЗАВЕРШЕН!            ║\n"
            "╚═══════════════════════════════════╝\n\n"
            "🎉 <b>Ваша матрица судьбы готова!</b>\n\n"
            "Изучите результаты выше и узнайте больше о себе.\n\n"
            "<i>💡 Совет: Сохраните результаты для дальнейшего изучения</i>",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Ошибка при расчете: {e}", exc_info=True)
        keyboard = [
            [InlineKeyboardButton("🔄 Попробовать снова", callback_data="calculate")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await processing_msg.edit_text(
            "╔═══════════════════════════════════╗\n"
            "║   ❌ ОШИБКА РАСЧЕТА             ║\n"
            "╚═══════════════════════════════════╝\n\n"
            "😔 <b>Произошла ошибка при расчете</b>\n\n"
            "Пожалуйста, попробуйте еще раз.\n\n"
            "💡 <i>Если ошибка повторяется, обратитесь к администратору</i>",
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
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
                text = (
                    "╔═══════════════════════════════════╗\n"
                    "║   📊 ИСТОРИЯ РАСЧЕТОВ            ║\n"
                    "╚═══════════════════════════════════╝\n\n"
                    "📭 <b>У вас пока нет сохраненных расчетов</b>\n\n"
                    "✨ Начните новый расчет прямо сейчас!"
                )
                keyboard = [
                    [InlineKeyboardButton("✨ Рассчитать матрицу", callback_data="calculate")],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                if update.callback_query:
                    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
                else:
                    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
                return
            
            text = (
                "╔═══════════════════════════════════╗\n"
                "║   📊 ИСТОРИЯ РАСЧЕТОВ            ║\n"
                "╚═══════════════════════════════════╝\n\n"
            )
            text += f"{create_section_header(f'Всего расчетов: {len(client.calculations)}', '📈')}"
            
            # Показываем последние 10
            for i, calc in enumerate(client.calculations[-10:], 1):
                date_str = calc.created_at.strftime("%d.%m.%Y %H:%M")
                text += f"<b>{i}.</b> 📅 {date_str}\n"
            
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
        "╔═══════════════════════════════════╗\n"
        "║   ⭐ ОЦЕНКА РАСЧЕТА              ║\n"
        "╚═══════════════════════════════════╝\n\n"
        "💬 <b>Насколько полезным был расчет матрицы?</b>\n\n"
        "Пожалуйста, выберите оценку от 1 до 5 звезд:\n\n"
        "<i>Ваше мнение очень важно для нас!</i>",
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
    
    stars_emoji = "⭐" * rating + "☆" * (5 - rating)
    
    await query.edit_message_text(
        f"╔═══════════════════════════════════╗\n"
        f"║   ⭐ СПАСИБО ЗА ОЦЕНКУ!          ║\n"
        f"╚═══════════════════════════════════╝\n\n"
        f"<b>{stars_emoji}</b>\n\n"
        f"Вы оценили расчет на <b>{rating}</b> {'звезд' if rating > 1 else 'звезду'} из 5.\n\n"
        f"🙏 <i>Ваше мнение помогает нам становиться лучше!</i>\n\n"
        f"💬 <i>Если у вас есть предложения, напишите администратору</i>",
        parse_mode=ParseMode.HTML
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена операции"""
    keyboard = [
        [InlineKeyboardButton("✨ Рассчитать матрицу", callback_data="calculate")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "╔═══════════════════════════════════╗\n"
        "║   ❌ ОПЕРАЦИЯ ОТМЕНЕНА           ║\n"
        "╚═══════════════════════════════════╝\n\n"
        "Вы отменили текущую операцию.\n\n"
        "Для начала нового расчета используйте кнопку ниже:",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
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
