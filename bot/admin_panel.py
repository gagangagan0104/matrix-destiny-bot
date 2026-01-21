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
        await update.message.reply_text("❌ У вас нет доступа к админ-панели.")
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
🔐 <b>Админ-панель</b>

📊 <b>Общая статистика:</b>
• Всего клиентов: {total_clients}
• Всего расчетов: {total_calculations}

📈 <b>За сегодня:</b>
• Новых клиентов: {clients_today}
• Расчетов: {calculations_today}

📅 <b>За последние 7 дней:</b>
• Новых клиентов: {clients_week}
• Расчетов: {calculations_week}
"""
        
        keyboard = [
            [InlineKeyboardButton("👥 Управление клиентами", callback_data="admin_clients")],
            [InlineKeyboardButton("📊 Детальная статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("📝 Последние расчеты", callback_data="admin_recent")],
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
        await query.edit_message_text("❌ У вас нет доступа.")
        return
    
    db = get_db_sync()
    try:
        per_page = 10
        offset = page * per_page
        
        clients = db.query(Client).order_by(desc(Client.created_at)).offset(offset).limit(per_page).all()
        total = db.query(Client).count()
        total_pages = (total + per_page - 1) // per_page
        
        if not clients:
            await query.edit_message_text("📭 Клиентов пока нет.")
            return
        
        text = f"👥 <b>Клиенты</b> (стр. {page + 1}/{total_pages})\n\n"
        
        for i, client in enumerate(clients, start=offset + 1):
            calc_count = len(client.calculations)
            text += f"{i}. <b>{client.name}</b>\n"
            text += f"   📅 {client.birth_date.strftime('%d.%m.%Y')}\n"
            text += f"   📊 Расчетов: {calc_count}\n"
            text += f"   🆔 ID: {client.id}\n\n"
        
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
        await query.edit_message_text("❌ У вас нет доступа.")
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
        
        text = "📊 <b>Детальная статистика</b>\n\n"
        text += "<b>Расчеты за последние 7 дней:</b>\n"
        
        for stat in daily_stats:
            date_str = stat.date.strftime('%d.%m')
            text += f"• {date_str}: {stat.count} расчетов\n"
        
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
        
        text += "\n<b>Топ-5 активных клиентов:</b>\n"
        for i, (client_id, name, count) in enumerate(top_clients, 1):
            text += f"{i}. {name}: {count} расчетов\n"
        
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
        await query.edit_message_text("❌ У вас нет доступа.")
        return
    
    db = get_db_sync()
    try:
        recent = db.query(MatrixCalculation).order_by(
            desc(MatrixCalculation.created_at)
        ).limit(10).all()
        
        if not recent:
            await query.edit_message_text("📭 Расчетов пока нет.")
            return
        
        text = "📝 <b>Последние расчеты</b>\n\n"
        
        for calc in recent:
            client = calc.client
            time_str = calc.created_at.strftime('%d.%m.%Y %H:%M')
            text += f"• <b>{client.name}</b>\n"
            text += f"  {time_str}\n"
            text += f"  🆔 Расчет #{calc.id}\n\n"
        
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
        await query.edit_message_text("❌ У вас нет доступа.")
        return
    
    text = """
⚙️ <b>Настройки</b>

Здесь можно настроить:
• Уведомления о новых расчетах
• Автоматические рассылки
• Шаблоны сообщений
• И другие параметры

(Функционал в разработке)
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
