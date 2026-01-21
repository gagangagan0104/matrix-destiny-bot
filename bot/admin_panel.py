"""Админ-панель для управления ботом"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from typing import Optional

from database.database import get_db_sync
from database.models import Client, MatrixCalculation
from config.admin import is_admin
import logging

logger = logging.getLogger(__name__)


async def admin_check(update: Update) -> bool:
    """Проверяет, является ли пользователь администратором"""
    user_id = update.effective_user.id
    return is_admin(user_id)


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главная панель администратора"""
    if not await admin_check(update):
        await update.message.reply_text(
            "╔═══════════════════════════════════╗\n"
            "║   ❌ ДОСТУП ЗАПРЕЩЕН            ║\n"
            "╚═══════════════════════════════════╝\n\n"
            "🔒 <b>У вас нет доступа к админ-панели</b>\n\n"
            "Обратитесь к администратору для получения доступа.",
            parse_mode=ParseMode.HTML
        )
        return
    
    db = get_db_sync()
    try:
        # Статистика
        total_clients = db.query(Client).count()
        total_calculations = db.query(MatrixCalculation).count()
        
        # За сегодня
        today = datetime.now().date()
        clients_today = db.query(Client).filter(
            func.date(Client.created_at) == today
        ).count()
        calculations_today = db.query(MatrixCalculation).filter(
            func.date(MatrixCalculation.created_at) == today
        ).count()
        
        # За последние 7 дней
        week_ago = datetime.now() - timedelta(days=7)
        clients_week = db.query(Client).filter(
            Client.created_at >= week_ago
        ).count()
        calculations_week = db.query(MatrixCalculation).filter(
            MatrixCalculation.created_at >= week_ago
        ).count()
        
        stats_text = f"""
╔═══════════════════════════════════╗
║   🔐 АДМИН-ПАНЕЛЬ                ║
╚═══════════════════════════════════╝

📊 <b>ОБЩАЯ СТАТИСТИКА</b>
{'─' * 30}
👥 Всего клиентов: <b>{total_clients}</b>
📈 Всего расчетов: <b>{total_calculations}</b>

📅 <b>ЗА СЕГОДНЯ</b>
{'─' * 30}
✨ Новых клиентов: <b>{clients_today}</b>
🔢 Расчетов: <b>{calculations_today}</b>

📆 <b>ЗА ПОСЛЕДНИЕ 7 ДНЕЙ</b>
{'─' * 30}
✨ Новых клиентов: <b>{clients_week}</b>
🔢 Расчетов: <b>{calculations_week}</b>

💡 <i>Выберите раздел для управления</i>
"""
        
        keyboard = [
            [InlineKeyboardButton("👥 Управление клиентами", callback_data="admin_clients")],
            [
                InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
                InlineKeyboardButton("📝 Последние расчеты", callback_data="admin_recent")
            ],
            [InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings")],
            [InlineKeyboardButton("🔙 Главное меню", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            stats_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    finally:
        db.close()


async def admin_clients(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
    """Список клиентов с пагинацией"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_check(update):
        await query.edit_message_text(
            "╔═══════════════════════════════════╗\n"
            "║   ❌ ДОСТУП ЗАПРЕЩЕН            ║\n"
            "╚═══════════════════════════════════╝\n\n"
            "🔒 <b>У вас нет доступа</b>\n\n"
            "Обратитесь к администратору.",
            parse_mode=ParseMode.HTML
        )
        return
    
    db = get_db_sync()
    try:
        per_page = 10
        offset = page * per_page
        
        clients = db.query(Client).order_by(desc(Client.created_at)).offset(offset).limit(per_page).all()
        total = db.query(Client).count()
        total_pages = (total + per_page - 1) // per_page
        
        if not clients:
            keyboard = [[InlineKeyboardButton("🔙 Назад в админ-панель", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "╔═══════════════════════════════════╗\n"
                "║   👥 УПРАВЛЕНИЕ КЛИЕНТАМИ        ║\n"
                "╚═══════════════════════════════════╝\n\n"
                "📭 <b>Клиентов пока нет</b>\n\n"
                "Как только появятся первые клиенты, они отобразятся здесь.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            return
        
        text = (
            f"╔═══════════════════════════════════╗\n"
            f"║   👥 УПРАВЛЕНИЕ КЛИЕНТАМИ        ║\n"
            f"╚═══════════════════════════════════╝\n\n"
            f"📄 <b>Страница {page + 1} из {total_pages}</b>\n"
            f"{'─' * 30}\n\n"
        )
        
        for i, client in enumerate(clients, start=offset + 1):
            calc_count = len(client.calculations)
            created_date = client.created_at.strftime('%d.%m.%Y') if hasattr(client, 'created_at') else 'N/A'
            text += f"<b>{i}.</b> 👤 <b>{client.name}</b>\n"
            text += f"   📅 Дата рождения: {client.birth_date.strftime('%d.%m.%Y')}\n"
            text += f"   📊 Расчетов: <b>{calc_count}</b>\n"
            text += f"   🆔 ID: <code>{client.id}</code>\n"
            text += f"   📝 Регистрация: {created_date}\n\n"
        
        keyboard = []
        
        # Кнопки навигации
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("◀️ Назад", callback_data=f"admin_clients_{page-1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("Вперед ▶️", callback_data=f"admin_clients_{page+1}"))
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("🔙 Назад в админ-панель", callback_data="admin_panel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    finally:
        db.close()


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Детальная статистика"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_check(update):
        await query.edit_message_text(
            "╔═══════════════════════════════════╗\n"
            "║   ❌ ДОСТУП ЗАПРЕЩЕН            ║\n"
            "╚═══════════════════════════════════╝\n\n"
            "🔒 <b>У вас нет доступа</b>\n\n"
            "Обратитесь к администратору.",
            parse_mode=ParseMode.HTML
        )
        return
    
    db = get_db_sync()
    try:
        # Статистика по дням за последние 30 дней
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        daily_stats = db.query(
            func.date(MatrixCalculation.created_at).label('date'),
            func.count(MatrixCalculation.id).label('count')
        ).filter(
            MatrixCalculation.created_at >= thirty_days_ago
        ).group_by(
            func.date(MatrixCalculation.created_at)
        ).order_by(desc('date')).limit(7).all()
        
        text = (
            "╔═══════════════════════════════════╗\n"
            "║   📊 ДЕТАЛЬНАЯ СТАТИСТИКА        ║\n"
            "╚═══════════════════════════════════╝\n\n"
        )
        
        text += f"📈 <b>РАСЧЕТЫ ЗА ПОСЛЕДНИЕ 7 ДНЕЙ</b>\n{'─' * 30}\n"
        
        if daily_stats:
            for stat in daily_stats:
                date_str = stat.date.strftime('%d.%m')
                bar_length = min(int(stat.count / max([s.count for s in daily_stats], default=1) * 20), 20)
                bar = "█" * bar_length + "░" * (20 - bar_length)
                text += f"📅 {date_str}: <b>{stat.count}</b> расчетов\n"
                text += f"   <code>{bar}</code>\n\n"
        else:
            text += "📭 Нет данных за этот период\n\n"
        
        # Топ клиентов
        top_clients = db.query(
            Client.id,
            Client.name,
            func.count(MatrixCalculation.id).label('calc_count')
        ).join(
            MatrixCalculation
        ).group_by(
            Client.id, Client.name
        ).order_by(desc('calc_count')).limit(5).all()
        
        text += f"🏆 <b>ТОП-5 АКТИВНЫХ КЛИЕНТОВ</b>\n{'─' * 30}\n"
        if top_clients:
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            for i, (client_id, name, count) in enumerate(top_clients, 1):
                medal = medals[i-1] if i <= 3 else f"{i}."
                text += f"{medal} <b>{name}</b>: <code>{count}</code> расчетов\n"
        else:
            text += "📭 Нет данных\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    finally:
        db.close()


async def admin_recent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Последние расчеты"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_check(update):
        await query.edit_message_text(
            "╔═══════════════════════════════════╗\n"
            "║   ❌ ДОСТУП ЗАПРЕЩЕН            ║\n"
            "╚═══════════════════════════════════╝\n\n"
            "🔒 <b>У вас нет доступа</b>\n\n"
            "Обратитесь к администратору.",
            parse_mode=ParseMode.HTML
        )
        return
    
    db = get_db_sync()
    try:
        recent = db.query(MatrixCalculation).order_by(
            desc(MatrixCalculation.created_at)
        ).limit(10).all()
        
        if not recent:
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "╔═══════════════════════════════════╗\n"
                "║   📝 ПОСЛЕДНИЕ РАСЧЕТЫ            ║\n"
                "╚═══════════════════════════════════╝\n\n"
                "📭 <b>Расчетов пока нет</b>\n\n"
                "Как только появятся первые расчеты, они отобразятся здесь.",
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML
            )
            return
        
        text = (
            "╔═══════════════════════════════════╗\n"
            "║   📝 ПОСЛЕДНИЕ РАСЧЕТЫ            ║\n"
            "╚═══════════════════════════════════╝\n\n"
        )
        
        for i, calc in enumerate(recent, 1):
            client = calc.client
            time_str = calc.created_at.strftime('%d.%m.%Y %H:%M')
            text += f"<b>{i}.</b> 👤 <b>{client.name}</b>\n"
            text += f"   📅 {time_str}\n"
            text += f"   🆔 ID: <code>{calc.id}</code>\n"
            text += f"   📊 Клиент ID: <code>{client.id}</code>\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
    finally:
        db.close()


async def admin_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройки админ-панели"""
    query = update.callback_query
    await query.answer()
    
    if not await admin_check(update):
        await query.edit_message_text(
            "╔═══════════════════════════════════╗\n"
            "║   ❌ ДОСТУП ЗАПРЕЩЕН            ║\n"
            "╚═══════════════════════════════════╝\n\n"
            "🔒 <b>У вас нет доступа</b>\n\n"
            "Обратитесь к администратору.",
            parse_mode=ParseMode.HTML
        )
        return
    
    text = (
        "╔═══════════════════════════════════╗\n"
        "║   ⚙️ НАСТРОЙКИ                    ║\n"
        "╚═══════════════════════════════════╝\n\n"
        "🔧 <b>ДОСТУПНЫЕ НАСТРОЙКИ</b>\n"
        "─" * 30 + "\n"
        "📢 Уведомления о новых расчетах\n"
        "📨 Автоматические рассылки\n"
        "📝 Шаблоны сообщений\n"
        "🔐 Управление правами доступа\n"
        "📊 Настройки аналитики\n\n"
        "💡 <i>Расширенный функционал в разработке</i>"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
