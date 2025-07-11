import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, CallbackQuery
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import NetworkError, TimedOut, TelegramError
from keep_alive import keep_alive
from database import (
    init_db, save_user_params, get_user_params,
    save_calculation_results, get_calculation_history, 
    set_target_weight, get_target_weight, get_last_calculation,
    track_user_action, register_user, get_user_statistics, format_statistics_message,
    get_nutrition_cards, save_weight, get_weight_history,
    clear_all_nutrition_cards, add_vitamin_cards, add_seasonal_cards, 
    add_nutrition_cards, add_diet_cards
)
from datetime import datetime
import sqlite3
from yookassa import Configuration, Payment
from yookassa_payment import YooKassaPayment
import uuid

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.environ.get('TELEGRAM_TOKEN')
YOOKASSA_SHOP_ID = os.environ.get('YOOKASSA_SHOP_ID')
YOOKASSA_SECRET_KEY = os.environ.get('YOOKASSA_SECRET_KEY')

# Проверка наличия необходимых переменных окружения
if not all([TOKEN, YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY]):
    logger.error("Missing required environment variables!")
    logger.error(f"TOKEN: {'Present' if TOKEN else 'Missing'}")
    logger.error(f"YOOKASSA_SHOP_ID: {'Present' if YOOKASSA_SHOP_ID else 'Missing'}")
    logger.error(f"YOOKASSA_SECRET_KEY: {'Present' if YOOKASSA_SECRET_KEY else 'Missing'}")
    raise ValueError("Missing required environment variables!")

# Настройка YooKassa
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY

# Инициализация YooKassa
yookassa = YooKassaPayment()

# Константы для callback_data
CALLBACK = {
    'MAIN_MENU': 'back_to_main',
    'TIPS_MENU': 'tips',
    'BACK_TO_TIPS': 'back_to_tips',
    'CALCULATE': 'calculate',
    'CALC_HISTORY': 'calc_history',
    'SET_TARGET': 'set_target',
    'DONATE': 'donate',
    'SHARE_BOT': 'share_bot',
    'TIPS': 'tips'
}

# Функции для создания клавиатур
def get_main_menu_keyboard():
    """Создает клавиатуру главного меню"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Рассчитать норму", callback_data="calculate")],
        [InlineKeyboardButton("📋 История расчетов", callback_data="calc_history")],
        [InlineKeyboardButton("💝 Поддержать бота", callback_data="donate")]
    ])

def get_tips_menu_keyboard(category, current_index=0):
    """Создает клавиатуру для меню карточек"""
    keyboard = []
    
    # Получаем карточки для категории
    cards = get_nutrition_cards(category)
    total_cards = len(cards)
    
    if total_cards > 0:
        # Добавляем кнопки навигации
        nav_buttons = []
        if current_index > 0:
            nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"prev_{category}"))
        if current_index < total_cards - 1:
            nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"next_{category}"))
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        # Добавляем кнопку возврата в меню
        keyboard.append([InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")])
    
    return InlineKeyboardMarkup(keyboard)

def get_card_navigation_keyboard(card_type):
    """Создает клавиатуру для навигации по карточкам"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Предыдущая карточка", callback_data=f"card_prev_{card_type}")],
        [InlineKeyboardButton("▶️ Следующая карточка", callback_data=f"card_next_{card_type}")],
        [InlineKeyboardButton("◀️ Назад в Полезное", callback_data=CALLBACK['BACK_TO_TIPS'])]
    ])

# Функции для создания сообщений
def get_main_menu_message(last_calculation=None):
    """Возвращает текст главного меню"""
    if last_calculation:
        return last_calculation["message"]
    return (
        "👋 *Добро пожаловать в НормаЖора!*\n\n"
        "Я помогу тебе:\n"
        "• Рассчитать норму питания\n\n"
        "💡 *Совет:* Если ты заблудился в меню, просто напиши /start\n\n"
        "Выбери действие:"
    )

def get_tips_menu_message():
    """Возвращает текст меню полезных советов"""
    return (
        '📚 *Раздел "Полезное"*\n\n'
        'В этом разделе ты найдешь информацию о:\n\n'
        '• *Сезонные продукты* - информация о сезонных овощах, фруктах и ягодах\n'
        '• *Таблички* - полезные трекеры и шаблоны для распечатки\n\n'
        '💡 *Главный совет:*\n'
        '• Лучший подход к питанию - это сбалансированный рацион с учетом КБЖУ\n'
        '• Любая диета должна быть адаптирована под твои индивидуальные потребности\n'
        '• Следи за балансом белков, жиров и углеводов\n'
        '• Учитывай свой уровень активности и цели\n'
        '• Помни, что здоровое питание - это образ жизни, а не временная мера'
    )

# Функция для безопасного редактирования сообщений
async def safe_edit_message(message, text, reply_markup=None, parse_mode="Markdown"):
    """Безопасно редактирует сообщение с обработкой ошибок"""
    try:
        await message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        try:
            # Если не удалось отредактировать, отправляем новое сообщение
            await message.reply_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        except Exception as e:
            logger.error(f"Error sending new message: {e}")

# Функция для безопасного редактирования медиа
async def safe_edit_media(message, media, reply_markup=None):
    """Безопасно редактирует медиа-сообщение с обработкой ошибок"""
    try:
        await message.edit_media(
            media=media,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error editing media: {e}")
        try:
            await message.reply_photo(
                photo=media.media,
                caption=media.caption,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error sending new media: {e}")
            # Если не удалось отправить медиа, отправляем текст
            await safe_edit_message(
                message,
                media.caption,
                reply_markup=reply_markup
            )

async def create_payment(amount, description):
    """Создание платежа через YooKassa"""
    try:
        logger.info(f"Creating payment for amount: {amount} RUB")
        logger.info(f"Using shop_id: {YOOKASSA_SHOP_ID}")
        
        payment = Payment.create({
            "amount": {
                "value": str(amount),
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": "https://t.me/norma_zhora_bot"
            },
            "capture": True,
            "description": description,
            "metadata": {
                "order_id": str(uuid.uuid4())
            }
        })
        
        if payment and payment.confirmation and payment.confirmation.confirmation_url:
            logger.info(f"Payment created successfully. Confirmation URL: {payment.confirmation.confirmation_url}")
            return payment
        else:
            logger.error("Payment created but confirmation URL is missing")
            return None
            
    except Exception as e:
        logger.error(f"Error creating payment: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {e.__dict__ if hasattr(e, '__dict__') else 'No details available'}")
        return None

async def handle_donation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатия на кнопку поддержки бота"""
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("300 ₽", callback_data="donate_300")],
        [InlineKeyboardButton("500 ₽", callback_data="donate_500")],
        [InlineKeyboardButton("1000 ₽", callback_data="donate_1000")],
        [InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        "💝 *Поддержка бота*\n\nВыбери сумму доната:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def process_donation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора суммы доната"""
    query = update.callback_query
    await query.answer()
    amount = int(query.data.split('_')[1])
    user_id = update.effective_user.id
    try:
        payment = yookassa.create_payment(amount, f"Донат для бота НормаЖора - {amount} ₽")
        payment_url = payment.confirmation.confirmation_url
        keyboard = [
            [InlineKeyboardButton("💳 Оплатить", url=payment_url)],
            [InlineKeyboardButton("◀️ Назад к выбору суммы", callback_data="donate")],
            [InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            f"💝 *Поддержка бота*\n\nСумма: {amount} ₽\n\nНажми на кнопку ниже, чтобы перейти к оплате:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        await query.message.reply_text(
            "❌ Произошла ошибка при создании платежа. Пожалуйста, попробуй позже.",
            reply_markup=get_main_menu_keyboard()
        )

# Инициализация базы данных при запуске
init_db()

# Очищаем все карточки и добавляем новые
clear_all_nutrition_cards()
add_vitamin_cards()
add_seasonal_cards()  # Добавляем карточки с сезонными продуктами
add_nutrition_cards()  # Добавляем карточки о питании
add_diet_cards()  # Добавляем карточки с диетами

# Константы для уровней активности
ACTIVITY_LEVELS = {
    "минимальная": 1.2,
    "низкая": 1.375,
    "средняя": 1.55,
    "высокая": 1.725,
    "очень высокая": 1.9
}

def get_activity_keyboard():
    """Создает клавиатуру для выбора уровня активности"""
    keyboard = [
        [InlineKeyboardButton("Минимальная", callback_data="activity_min")],
        [InlineKeyboardButton("Низкая", callback_data="activity_low")],
        [InlineKeyboardButton("Средняя", callback_data="activity_medium")],
        [InlineKeyboardButton("Высокая", callback_data="activity_high")],
        [InlineKeyboardButton("Очень высокая", callback_data="activity_very_high")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def calculate_nutrition_norms(weight, height, age, gender, activity_level):
    """Рассчитывает нормы питания"""
    # Базовый обмен веществ (формула Миффлина-Сан Жеора)
    if gender == "мужской":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
        
    # Умножаем на коэффициент активности
    activity_multiplier = ACTIVITY_LEVELS.get(activity_level, 1.55)
    maintenance_calories = bmr * activity_multiplier
    
    # Рассчитываем дефицит и профицит
    deficit_calories_15 = maintenance_calories * 0.85
    deficit_calories_20 = maintenance_calories * 0.8
    surplus_calories = maintenance_calories * 1.1
    
    # Рассчитываем БЖУ согласно научным рекомендациям с учетом возраста
    # Определяем возрастную категорию
    if age < 18:
        age_category = "подросток"
    elif age < 30:
        age_category = "молодой"
    elif age < 50:
        age_category = "средний"
    elif age < 65:
        age_category = "зрелый"
    else:
        age_category = "пожилой"
    
    # Белки: современные рекомендации с учетом возраста, пола, активности и климакса
    # Базовые нормы по возрасту (г/кг веса)
    base_protein_multipliers = {
        "подросток": (1.8, 2.2),  # Высокая потребность для роста и развития
        "молодой": (1.8, 2.2),    # Стандартные рекомендации для активного возраста
        "средний": (1.8, 2.0),    # Поддержание мышечной массы
        "зрелый": (1.8, 2.0),     # Увеличенная потребность для предотвращения саркопении
        "пожилой": (1.6, 1.8)     # Минимальные для поддержания здоровья, но достаточные
    }
    
    # Корректировка по полу
    gender_protein_multiplier = {
        "мужской": 1.05,  # Мужчинам нужно немного больше белка
        "женский": 1.0
    }
    
    # Корректировка по уровню активности
    activity_protein_multiplier = {
        "минимальная": 1.0,      # Сидячий образ жизни
        "низкая": 1.05,          # Легкие тренировки
        "средняя": 1.1,          # Умеренные тренировки
        "высокая": 1.15,         # Интенсивные тренировки
        "очень высокая": 1.2     # Ежедневные интенсивные тренировки
    }
    
    # Корректировка по климаксу для женщин (45-55 лет - перименопауза, 55+ - постменопауза)
    menopause_multiplier = 1.0
    if gender == "женский":
        if age >= 45 and age <= 55:
            menopause_multiplier = 1.1  # Перименопауза: повышенная потребность в белке
        elif age > 55:
            menopause_multiplier = 1.15  # Постменопауза: еще больше белка для предотвращения остеопороза
    
    # Получаем базовые множители для возраста
    protein_min_mult, protein_max_mult = base_protein_multipliers.get(age_category, (1.8, 2.2))
    
    # Применяем корректировки по полу, активности и климаксу
    gender_mult = gender_protein_multiplier.get(gender, 1.0)
    activity_mult = activity_protein_multiplier.get(activity_level, 1.1)
    
    # Рассчитываем финальные нормы белков
    protein_min = weight * protein_min_mult * gender_mult * activity_mult * menopause_multiplier
    protein_max = weight * protein_max_mult * gender_mult * activity_mult * menopause_multiplier
    
    # Жиры: корректировка по полу, возрасту и климаксу
    if gender == "мужской":
        if age < 18:
            fat_percentage_min, fat_percentage_max = 0.25, 0.35  # Подростки: больше жиров
        elif age < 30:
            fat_percentage_min, fat_percentage_max = 0.20, 0.30  # Молодые мужчины
        elif age < 50:
            fat_percentage_min, fat_percentage_max = 0.20, 0.30  # Средний возраст
        else:
            fat_percentage_min, fat_percentage_max = 0.25, 0.35  # Пожилые: больше жиров
        fat_min_per_kg = 0.8
    else:
        # Учет климакса для женщин
        if age < 18:
            fat_percentage_min, fat_percentage_max = 0.30, 0.40  # Подростки: больше жиров
        elif age < 30:
            fat_percentage_min, fat_percentage_max = 0.25, 0.35  # Молодые женщины
        elif age < 45:
            fat_percentage_min, fat_percentage_max = 0.25, 0.35  # Средний возраст
        elif age < 55:
            # Перименопауза: немного больше жиров для гормональной поддержки
            fat_percentage_min, fat_percentage_max = 0.30, 0.40
        else:
            # Постменопауза: больше жиров для усвоения жирорастворимых витаминов
            fat_percentage_min, fat_percentage_max = 0.30, 0.40
        fat_min_per_kg = 0.9
    
    # Рассчитываем жиры от калорийности
    fat_min_calories = maintenance_calories * fat_percentage_min
    fat_max_calories = maintenance_calories * fat_percentage_max
    fat_min = max(fat_min_calories / 9, weight * fat_min_per_kg)  # Минимум из расчета и веса
    fat_max = fat_max_calories / 9
    
    # Углеводы: оставшиеся калории после белков и жиров
    # Используем дефицит калорий для расчета углеводов
    protein_calories_min = protein_min * 4
    protein_calories_max = protein_max * 4
    fat_calories_min = fat_min * 9
    fat_calories_max = fat_max * 9
    
    # Углеводы для дефицита (похудение)
    remaining_calories_deficit = deficit_calories_15 - protein_calories_min - fat_calories_min
    carbs_min = max(remaining_calories_deficit / 4, 50)  # Минимум 50г углеводов
    
    # Углеводы для профицита (набор массы)
    remaining_calories_surplus = surplus_calories - protein_calories_max - fat_calories_max
    carbs_max = remaining_calories_surplus / 4
    
    # Рассчитываем ИМТ
    height_m = height / 100
    bmi = weight / (height_m * height_m)
    
    # Определяем категорию ИМТ
    if bmi < 18.5:
        bmi_category = "Недостаточный вес"
    elif bmi < 25:
        bmi_category = "Нормальный вес"
    elif bmi < 30:
        bmi_category = "Избыточный вес"
    else:
        bmi_category = "Ожирение"
        
    # Рассчитываем норму воды согласно научным рекомендациям с учетом возраста, пола, активности и климакса
    # Базовая норма: 30-35мл на кг веса
    
    # Корректировка по полу
    if gender == "мужской":
        water_multiplier = 1.1  # Мужчинам нужно больше воды
    else:
        water_multiplier = 1.0
    
    # Корректировка по возрасту (используем уже определенную age_category)
    age_water_multipliers = {
        "подросток": 1.1,    # Подростки: повышенная потребность в воде
        "молодой": 1.0,      # Молодые: стандартная норма
        "средний": 0.95,     # Средний возраст: небольшое снижение
        "зрелый": 0.9,       # Зрелый возраст: снижение потребности
        "пожилой": 0.85      # Пожилые: значительное снижение
    }
    age_multiplier = age_water_multipliers.get(age_category, 1.0)
    
    # Корректировка по активности
    activity_water_multiplier = {
        "минимальная": 1.0,
        "низкая": 1.05,
        "средняя": 1.1,
        "высокая": 1.15,
        "очень высокая": 1.2
    }.get(activity_level, 1.1)
    
    # Корректировка по климаксу для женщин
    menopause_water_multiplier = 1.0
    if gender == "женский":
        if age >= 45 and age <= 55:
            menopause_water_multiplier = 1.05  # Перименопауза: немного больше воды
        elif age > 55:
            menopause_water_multiplier = 1.1   # Постменопауза: больше воды для вывода токсинов
    
    # Базовая норма воды в зависимости от возраста
    base_water_per_kg = 30
    
    # Рассчитываем норму воды
    water_norm_min = weight * base_water_per_kg * water_multiplier * age_multiplier * activity_water_multiplier * menopause_water_multiplier
    water_norm_max = water_norm_min * 1.1  # +10% для индивидуальных различий
    
    # Рассчитываем рекомендуемые шаги с учетом возраста, пола и активности
    # Базовые нормы шагов
    base_steps = {
        "минимальная": 6000,
        "низкая": 8000,
        "средняя": 10000,
        "высокая": 12000,
        "очень высокая": 15000
    }
    
    # Корректировка по возрасту
    age_steps_multiplier = {
        "подросток": 1.1,    # Подростки: больше активности
        "молодой": 1.0,      # Молодые: стандартная норма
        "средний": 0.95,     # Средний возраст: небольшое снижение
        "зрелый": 0.9,       # Зрелый возраст: снижение активности
        "пожилой": 0.8       # Пожилые: значительное снижение
    }.get(age_category, 1.0)
    
    # Корректировка по полу
    gender_steps_multiplier = {
        "мужской": 1.05,  # Мужчинам рекомендуется больше шагов
        "женский": 1.0
    }.get(gender, 1.0)
    
    # Корректировка по климаксу для женщин
    menopause_steps_multiplier = 1.0
    if gender == "женский":
        if age >= 45 and age <= 55:
            menopause_steps_multiplier = 0.95  # Перименопауза: немного меньше активности
        elif age > 55:
            menopause_steps_multiplier = 0.9   # Постменопауза: снижение активности
    
    # Рассчитываем рекомендуемые шаги
    base_steps_for_activity = base_steps.get(activity_level, 10000)
    recommended_steps_min = int(base_steps_for_activity * age_steps_multiplier * gender_steps_multiplier * menopause_steps_multiplier * 0.9)
    recommended_steps_max = int(base_steps_for_activity * age_steps_multiplier * gender_steps_multiplier * menopause_steps_multiplier * 1.1)
    
    return {
        'bmr': round(bmr),
        'maintenance_calories': round(maintenance_calories),
        'deficit_calories_15': round(deficit_calories_15),
        'deficit_calories_20': round(deficit_calories_20),
        'surplus_calories': round(surplus_calories),
        'protein_min': round(protein_min),
        'protein_max': round(protein_max),
        'fat_min': round(fat_min),
        'fat_max': round(fat_max),
        'carbs_min': round(carbs_min),
        'carbs_max': round(carbs_max),
        'bmi': round(bmi, 1),
        'bmi_category': bmi_category,
        'water_norm_min': round(water_norm_min),
        'water_norm_max': round(water_norm_max),
        'recommended_steps_min': recommended_steps_min,
        'recommended_steps_max': recommended_steps_max
    }

def format_calculation_results(results):
    """Форматирует результаты расчета в текст"""
    return (
        f"📊 *Результаты расчета*\n\n"
        f"• Базовый обмен веществ: {results['bmr']} ккал\n"
        f"• Норма калорий для поддержания текущего веса: {results['maintenance_calories']} ккал\n"
        f"• Безопасный дефицит 15% для похудения: {results['deficit_calories_15']} ккал\n"
        f"• Дефицит 20%: {results['deficit_calories_20']} ккал\n"
        f"• Профицит 10%: {results['surplus_calories']} ккал\n\n"
        f"🥗 *Рекомендуемые БЖУ:*\n"
        f"🥩 *Белки:* {results['protein_min']}-{results['protein_max']}г\n"
        f"🥑 *Жиры:* {results['fat_min']}-{results['fat_max']}г\n"
        f"🍚 *Углеводы:* {results['carbs_min']}-{results['carbs_max']}г\n\n"
        f"💧 *Норма воды:*\n"
        f"• {results['water_norm_min']}-{results['water_norm_max']}мл в день\n"
        f"• Это примерно {int(results['water_norm_min']/250)}-{int(results['water_norm_max']/250)} стаканов\n\n"
        f"👣 *Рекомендуемые шаги:* {results['recommended_steps_min']}-{results['recommended_steps_max']}\n\n"
        f"📏 *ИМТ:* {results['bmi']} ({results['bmi_category']})"
    )

async def calculate_norm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рассчитывает нормы питания на основе введенных параметров"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Получаем сохраненные параметры
    weight = context.user_data.get('weight')
    height = context.user_data.get('height')
    age = context.user_data.get('age')
    gender = context.user_data.get('gender')
    activity_level = context.user_data.get('activity_level')
    
    # Добавить проверку на отрицательные значения
    if any(param <= 0 for param in [weight, height, age]):
        raise ValueError("Параметры должны быть положительными числами")
    
    if not all([weight, height, age, gender, activity_level]):
        await query.answer("Пожалуйста, сначала введите все необходимые параметры")
        return
    
    # Рассчитываем нормы
    results = calculate_nutrition_norms(
        weight=float(weight),
        height=float(height),
        age=int(age),
        gender=gender,
        activity_level=activity_level
    )
    
    # Сохраняем результаты
    user_id = update.effective_user.id
    params = {
        'weight': float(weight),
        'height': float(height),
        'age': int(age),
        'gender': gender,
        'activity_level': activity_level
    }
    
    save_calculation_results(user_id, results, params)
    
    # Формируем сообщение с результатами
    message = format_calculation_results(results)
    
    # Отправляем результаты
    await query.message.edit_text(
        message,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    if isinstance(context.error, NetworkError):
        logger.error("Network error occurred. Attempting to reconnect...")
        await asyncio.sleep(5)  # Ждем 5 секунд перед повторной попыткой
        return
    
    if isinstance(context.error, TimedOut):
        logger.error("Request timed out. Retrying...")
        await asyncio.sleep(3)
        return
    
    # Отправляем сообщение пользователю об ошибке
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "😔 Произошла ошибка. Пожалуйста, попробуйте позже или начните сначала с помощью команды /start"
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    user_id = user.id
    
    # Регистрируем пользователя
    register_user(user_id, user.username, user.first_name, user.last_name)
    
    # Отслеживаем действие
    track_user_action(user_id, "start_bot")
    
    context.user_data.pop("activity_keyboard_shown", None)
    keyboard = get_main_menu_keyboard()
    await update.message.reply_text(
        get_main_menu_message(),
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для просмотра статистики (только для администратора)"""
    user_id = update.effective_user.id
    
    # Проверяем, является ли пользователь администратором
    # Замените ADMIN_USER_ID на ваш ID в Telegram
    ADMIN_USER_ID = 123456789  # Замените на ваш ID
    
    if user_id != ADMIN_USER_ID:
        await update.message.reply_text(
            "❌ У вас нет доступа к этой команде.",
            parse_mode="Markdown"
        )
        return
    
    # Получаем статистику
    stats = get_user_statistics()
    message = format_statistics_message(stats)
    
    keyboard = [
        [InlineKeyboardButton("🔄 Обновить", callback_data="refresh_stats")],
        [InlineKeyboardButton("📅 За сегодня", callback_data="stats_today")],
        [InlineKeyboardButton("📊 За неделю", callback_data="stats_week")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопок статистики"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    ADMIN_USER_ID = 123456789  # Замените на ваш ID
    
    if user_id != ADMIN_USER_ID:
        await query.message.edit_text(
            "❌ У вас нет доступа к этой функции.",
            parse_mode="Markdown"
        )
        return
    
    if query.data == "refresh_stats":
        stats = get_user_statistics()
        message = format_statistics_message(stats)
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="refresh_stats")],
            [InlineKeyboardButton("📅 За сегодня", callback_data="stats_today")],
            [InlineKeyboardButton("📊 За неделю", callback_data="stats_week")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    
    elif query.data == "stats_today":
        from database import get_daily_stats
        today_stats = get_daily_stats()
        message = f"📅 *Статистика за сегодня ({today_stats['date']})*\n\n"
        message += f"👥 Новых пользователей: {today_stats['new_users']}\n"
        message += f"🔄 Активных пользователей: {today_stats['active_users']}\n"
        message += f"🎯 Расчетов: {today_stats['calculations']}\n"
        message += f"⚖️ Записей веса: {today_stats['weight_entries']}\n"
        
        keyboard = [
            [InlineKeyboardButton("📊 Общая статистика", callback_data="refresh_stats")],
            [InlineKeyboardButton("📅 За сегодня", callback_data="stats_today")],
            [InlineKeyboardButton("📊 За неделю", callback_data="stats_week")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    
    elif query.data == "stats_week":
        from database import get_popular_actions
        popular_actions = get_popular_actions(7)
        message = "📊 *Популярные действия за неделю:*\n\n"
        
        for action, count in popular_actions.items():
            action_emoji = {
                "start_bot": "🚀",
                "calculate": "🎯", 
                "tips": "📚",
                "donate": "💝",
                "about_bot": "ℹ️"
            }.get(action, "📝")
            message += f"{action_emoji} {action}: {count}\n"
        
        keyboard = [
            [InlineKeyboardButton("📊 Общая статистика", callback_data="refresh_stats")],
            [InlineKeyboardButton("📅 За сегодня", callback_data="stats_today")],
            [InlineKeyboardButton("📊 За неделю", callback_data="stats_week")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(message, reply_markup=reply_markup, parse_mode="Markdown")

async def about_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    track_user_action(user_id, "about_bot")
    
    about_text = (
        "🤖 *О боте НормаЖора*\n\n"
        "Я - твой персональный помощник по питанию и здоровому образу жизни. Вот что я умею:\n\n"
        "🎯 *Расчет норм питания:*\n"
        "• Базовый метаболизм\n"
        "• Норма калорий для поддержания текущего веса\n"
        "• Дефицит калорий для похудения\n"
        "• Профицит калорий для набора массы\n"
        "• Определяю ИМТ и его категорию\n"
        "• Рекомендую оптимальное количество шагов в день\n\n"
        "📚 *Полезная информация:*\n"
        "• Информация о сезонных продуктах\n"
        "• Полезные таблички и трекеры для распечатки\n"
        "• Советы по физической активности\n\n"
        "💡 *Особенности:*\n"
        "• Учитываю расчеты исходя из возраста, пола\n"
        "• Адаптирую рекомендации под твой образ жизни\n"
        "• Даю безопасные рекомендации по изменению веса\n"
        "• Регулярно добавляю новую информацию\n"
        "💝 *Поддержка бота:*\n"
        "Если тебе нравится бот и ты хочешь поддержать его развитие, ты можешь сделать донат любой удобной суммой. Это поможет сделать бота еще лучше!"
    )
    keyboard = [
        [InlineKeyboardButton("💝 Поддержать бота", callback_data="donate")],
        [InlineKeyboardButton("📢 Поделиться ботом", callback_data="share_bot")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(
        about_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id

    # --- ВЛОЖЕННЫЕ МЕНЮ ДЛЯ 'ПОЛЕЗНОЕ' ---
    # Удалено всё, что связано с tips_seasonal, seasonal_card, tips_tables и навигацией по таблицам
    
    if query.data == CALLBACK['MAIN_MENU']:
        track_user_action(user_id, "back_to_main")
        await show_main_menu(update, context)
        return
    
    if query.data == CALLBACK['TIPS']:
        track_user_action(user_id, "tips")
        await show_tips_menu(update, context)
        return
    
    if query.data == "back_to_menu":
        track_user_action(user_id, "back_to_menu")
        await show_tips_menu(update, context)
        return
    
    # Обработка категорий карточек
    if query.data.startswith("tips_"):
        track_user_action(user_id, f"tips_{query.data.split('_')[1]}")
        category = query.data.split("_")[1]
        cards = get_nutrition_cards(category)
        if cards:
            current_card = cards[0]
            caption = current_card[4]  # description находится в 5-м элементе
            keyboard = [
                [InlineKeyboardButton("◀️", callback_data=f"card_prev_{category}")],
                [InlineKeyboardButton("▶️", callback_data=f"card_next_{category}")],
                [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_tips")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.edit_text(
                text=caption,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        return
    
    # Обработка навигации по карточкам
    if query.data.startswith(("prev_", "next_")):
        track_user_action(user_id, "card_navigation")
        action, category = query.data.split("_")
        cards = get_nutrition_cards(category)
        if not cards:
            return
            
        # Получаем текущий индекс из контекста
        current_index = context.user_data.get(f"{category}_index", 0)
        
        # Обновляем индекс
        if action == "prev" and current_index > 0:
            current_index -= 1
        elif action == "next" and current_index < len(cards) - 1:
            current_index += 1
            
        # Сохраняем новый индекс
        context.user_data[f"{category}_index"] = current_index
        
        # Показываем карточку
        current_card = cards[current_index]
        caption = current_card[4]  # description находится в 5-м элементе
        await query.edit_message_text(
            text=caption,
            parse_mode='Markdown',
            reply_markup=get_tips_menu_keyboard(category, current_index)
        )
        return
    
    if query.data == "new_calculation":
        track_user_action(user_id, "new_calculation")
        # Очищаем данные предыдущего расчета
        for key in list(context.user_data.keys()):
            if key.startswith("current_") or key in ["state", "calc_mode"]:
                context.user_data.pop(key)
        context.user_data.pop('weight', None)
        context.user_data.pop('height', None)
        context.user_data.pop('age', None)
        context.user_data.pop('gender', None)
        context.user_data.pop('activity_level', None)
        context.user_data.pop('calc_mode', None)
        
        keyboard = [
            [InlineKeyboardButton("Для себя", callback_data="calc_self")],
            [InlineKeyboardButton("Для друга", callback_data="calc_friend")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            "🎯 *Расчет нормы питания*\n\n"
            "Для кого ты хочешь рассчитать норму?\n\n"
            "• Для себя - расчет будет сохранен в твоей истории\n"
            "• Для друга - разовый расчет без сохранения\n\n"
            "Выбери вариант:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    elif query.data == "tips":
        track_user_action(user_id, "tips_menu")
        keyboard = get_tips_menu_keyboard()
        
        # Используем edit_text вместо reply_text для удобного чтения
        await query.message.edit_text(
            get_tips_menu_message(),
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    elif query.data == "confirm_target_":
        track_user_action(user_id, "confirm_target")
        try:
            target_weight = float(query.data.split("_")[2])
            user_id = update.effective_user.id
            set_target_weight(user_id, target_weight)
            
            # Удалённый функционал управления весом
            context.user_data.pop("state", None)  # Сбрасываем состояние после успешной установки цели
            
            # Возвращаемся в главное меню
            await back_to_main(update, context)
            
            return
        except Exception as e:
            logger.error(f"Error in confirm_target: {e}")
            keyboard = [
                [InlineKeyboardButton("🎯 Рассчитать норму", callback_data="calculate")],
                [InlineKeyboardButton("📚 Полезное", callback_data="tips")],
                [InlineKeyboardButton("ℹ️ О боте", callback_data="about_bot")],
                [InlineKeyboardButton("💝 Поддержать бота", callback_data="donate")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                "❌ Произошла ошибка при установке цели. Пожалуйста, попробуйте снова.",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return

    if query.data == "cancel_set_target":
        track_user_action(user_id, "cancel_set_target")
        context.user_data.pop("state", None) # Сбрасываем состояние при отмене установки цели
        await back_to_main(update, context)
        return

    if query.data == "calculate":
        track_user_action(user_id, "calculate")
        keyboard = [
            [InlineKeyboardButton("Для себя", callback_data="calc_self")],
            [InlineKeyboardButton("Для друга", callback_data="calc_friend")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            "🎯 *Расчет нормы питания*\n\n"
            "Для кого ты хочешь рассчитать норму?\n\n"
            "• Для себя - расчет будет сохранен в твоей истории\n"
            "• Для друга - разовый расчет без сохранения\n\n"
            "Выбери вариант:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    elif query.data == "calc_self":
        track_user_action(user_id, "calc_self")
        context.user_data["calc_mode"] = "self"
        print(f"User {user_id}: Set calc_mode = 'self'")
        keyboard = [
            [InlineKeyboardButton("Мужской", callback_data="gender_male")],
            [InlineKeyboardButton("Женский", callback_data="gender_female")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            "👤 *Расчет для себя*\n\n"
            "Твои параметры и результаты будут сохранены в истории.\n"
            "Пол:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    elif query.data == "calc_friend":
        track_user_action(user_id, "calc_friend")
        context.user_data["calc_mode"] = "friend"
        print(f"User {user_id}: Set calc_mode = 'friend'")
        keyboard = [
            [InlineKeyboardButton("Мужской", callback_data="gender_male_friend")],
            [InlineKeyboardButton("Женский", callback_data="gender_female_friend")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            "👥 *Расчет для друга*\n\n"
            "Это разовый расчет, результаты не будут сохранены.\n"
            "Поделись потом с другом результатом😉\n\n"
            "Выбери пол:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    elif query.data == "set_target":
        track_user_action(user_id, "set_target")
        # Получаем текущую цель пользователя
        user_params = get_user_params(update.effective_user.id)
        current_target = user_params.get('target_weight') if user_params else None
        
        message = "🎯 *Установка цели по весу*\n\n"
        if current_target:
            message += f"Текущая цель: `{current_target}` кг\n\n"
            message += "Хочешь установить новую цель?\n\n"
            
        message += "Введи желаемый вес в кг (например, 55.5):"
        
        keyboard = [
            [InlineKeyboardButton("◀️ Назад в Управление весом", callback_data="back_to_weight_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        context.user_data["state"] = "set_target" # Устанавливаем состояние для обработки ввода
        return # Завершаем обработку здесь, ожидая ввод
    elif query.data == "donate":
        track_user_action(user_id, "donate")
        await handle_donation(update, context)
        return
    elif query.data == "share_bot":
        track_user_action(user_id, "share_bot")
        await share_bot(update, context)
        return
    elif query.data == "back_to_weight":
        track_user_action(user_id, "back_to_weight")
        keyboard = [[InlineKeyboardButton("◀️ Назад к выбору пола", callback_data="back_to_gender")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            "⚖️ Введи вес в кг (например, 60):",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        context.user_data["state"] = "weight"
        return
    elif query.data == "back_to_gender":
        track_user_action(user_id, "back_to_gender")
        keyboard = [
            [InlineKeyboardButton("Мужской", callback_data="gender_male")],
            [InlineKeyboardButton("Женский", callback_data="gender_female")],
            [InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            "👤 Выбери пол:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        context.user_data["state"] = "gender"
        return
    elif query.data == "back_to_age":
        track_user_action(user_id, "back_to_age")
        keyboard = [[InlineKeyboardButton("◀️ Назад к росту", callback_data="back_to_weight")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            "👤 Введи возраст (например, 25):",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        context.user_data["state"] = "age"
        return

async def handle_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data.startswith("gender_"):
        # Определяем пол и режим расчета
        if query.data == "gender_male" or query.data == "gender_male_friend":
            gender = "мужской"
            weight_example = "80.5"
            height_example = "175"
            track_user_action(user_id, "gender_male")
        else:
            gender = "женский"
            weight_example = "60.5"
            height_example = "165"
            track_user_action(user_id, "gender_female")
            
        context.user_data["gender"] = gender
        
        keyboard = [
            [InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text(
            f"⚖️ Введи вес в кг (например, {weight_example}):",
            reply_markup=reply_markup
        )
        context.user_data["state"] = "weight"
        context.user_data["weight_example"] = weight_example
        context.user_data["height_example"] = height_example

async def handle_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора уровня активности"""
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception as e:
        logger.error(f"Error answering callback query: {e}")
        return

    user_id = update.effective_user.id
    track_user_action(user_id, f"activity_{query.data.replace('activity_', '')}")

    # Проверяем, что мы в правильном состоянии
    if context.user_data.get('state') != 'activity':
        logger.info("Activity handler called but state is not 'activity'")
        return

    # Получаем уровень активности из callback_data
    activity_level = query.data.replace('activity_', '')
    
    # Проверяем валидность уровня активности
    activity_mapping = {
        'min': 'минимальная',
        'low': 'низкая', 
        'medium': 'средняя',
        'high': 'высокая',
        'very_high': 'очень высокая'
    }
    
    if activity_level not in activity_mapping:
        logger.error(f"Invalid activity level: {activity_level}")
        return
        
    activity_level = activity_mapping[activity_level]
    context.user_data['activity_level'] = activity_level

    # Получаем все параметры
    weight = context.user_data.get('weight')
    height = context.user_data.get('height')
    age = context.user_data.get('age')
    gender = context.user_data.get('gender')

    if not all([weight, height, age, gender, activity_level]):
        logger.error("Missing parameters for calculation")
        await query.message.reply_text(
            "❌ Ошибка: не все параметры заполнены. Начни расчет заново.",
            reply_markup=get_main_menu_keyboard()
        )
        return

    try:
        # Рассчитываем нормы
        results = calculate_nutrition_norms(
            weight=float(weight),
            height=float(height),
            age=int(age),
            gender=gender,
            activity_level=activity_level
        )

        # Сохраняем результаты только если это расчет для себя
        calc_mode = context.user_data.get('calc_mode')
        print(f"User {update.effective_user.id}: calc_mode = {calc_mode}")
        
        if calc_mode == 'self':
            user_id = update.effective_user.id
            params = {
                'weight': float(weight),
                'height': float(height),
                'age': int(age),
                'gender': gender,
                'activity_level': activity_level
            }
            print(f"Saving calculation for user {user_id} with calc_mode = {calc_mode}")
            save_calculation_results(user_id, results, params)
            track_user_action(user_id, "calculation_completed")
        else:
            print(f"Not saving calculation for user {update.effective_user.id} because calc_mode = {calc_mode}")

        # Формируем сообщение с результатами
        message = format_calculation_results(results)

        # Сброс состояния пользователя
        context.user_data.pop("state", None)
        context.user_data.pop("activity_keyboard_shown", None)
        context.user_data.pop("calc_mode", None)

        # Отправляем результаты новым сообщением
        await query.message.edit_text(
            message,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
        
        logger.info(f"Calculation completed successfully for user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in calculation: {e}")
        await query.message.reply_text(
            "❌ Произошла ошибка при расчете. Пожалуйста, попробуй снова.",
            reply_markup=get_main_menu_keyboard()
        )

async def share_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик отправки результатов расчета другу"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(
        "Чтобы поделиться результатами, просто перешли это сообщение другу или сделай скриншот",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_target_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ввода целевого веса"""
    try:
        target_weight = float(update.message.text.replace(',', '.'))
        if target_weight <= 0 or target_weight > 300:
            await update.message.reply_text(
                "❌ Пожалуйста, введите корректный вес (от 1 до 300 кг):",
                reply_markup=get_main_menu_keyboard()
            )
            return
            
        user_id = update.effective_user.id
        set_target_weight(user_id, target_weight)
        
        await update.message.reply_text(
            f"✅ Целевой вес ({target_weight} кг) успешно установлен!",
            reply_markup=get_main_menu_keyboard()
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите число:",
            reply_markup=get_main_menu_keyboard()
        )

async def show_calculation_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    track_user_action(user_id, "calc_history")
    
    if query.data == "calc_history":
        history = list(get_calculation_history(user_id))
        
        if not history:
            keyboard = [
                [InlineKeyboardButton("🎯 Рассчитать норму", callback_data="calculate")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(
                "📊 У тебя пока нет сохраненных расчетов.\n"
                "Давай сделаем первый расчет!",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return
        
        message = "📊 *История расчетов:*\n\n"
        for calc in history:
            try:
                # Преобразуем строку даты в объект datetime
                # SQLite возвращает дату в формате YYYY-MM-DD HH:MM:SS
                date_obj = datetime.strptime(calc['date'], "%Y-%m-%d %H:%M:%S")
                # Форматируем дату в нужном формате
                date_str = date_obj.strftime("%d.%m.%Y")
                message += f"📅 *{date_str}*\n"
            except (ValueError, TypeError) as e:
                # Если формат даты неверный, используем дату как есть
                message += f"📅 *{calc['date']}*\n"
            
            message += f"👤 *Параметры:*\n"
            message += f"• Вес: {calc['weight']} кг\n"
            message += f"• Рост: {calc['height']} см\n"
            message += f"• Возраст: {calc['age']} лет\n"
            message += f"• Активность: {calc['activity_level']}\n\n"
            message += f"🎯 *Расчетные нормы:*\n"
            message += f"• Базовый метаболизм (BMR): {calc['bmr']} ккал\n"
            message += f"• Норма калорий: {calc['maintenance_calories']} ккал\n"
            message += f"• Дефицит (15%): {calc['deficit_calories_15']} ккал\n"
            message += f"• Дефицит (20%): {calc['deficit_calories_20']} ккал\n"
            message += f"• Профицит (+10%): {calc['surplus_calories']} ккал\n\n"
            message += f"🥗 *БЖУ:*\n"
            message += f"• Белки: {calc['protein_min']}-{calc['protein_max']}г\n"
            message += f"• Жиры: {calc['fat_min']}-{calc['fat_max']}г\n"
            message += f"• Углеводы: {calc['carbs_min']}-{calc['carbs_max']}г\n\n"
            message += f"📏 *ИМТ:*\n"
            message += f"• Индекс: {calc['bmi']:.1f}\n"
            message += f"• Категория: {calc['bmi_category']}\n\n"
            message += f"💧 *Норма воды:*\n"
            message += f"• {int(calc['water_norm_min'])}-{int(calc['water_norm_max'])} мл в день\n"
            message += f"• Это примерно {int(calc['water_norm_min']/250)}-{int(calc['water_norm_max']/250)} стаканов\n\n"
            
            # Добавляем рекомендуемое количество шагов из истории, если есть
            if 'recommended_steps_min' in calc and 'recommended_steps_max' in calc:
                message += f"🚶 *Рекомендуемое количество шагов:*\n"
                message += f"• {calc['recommended_steps_min']}-{calc['recommended_steps_max']} шагов в день\n\n"

            message += "➖➖➖➖➖➖➖➖➖➖\n\n"
        
        keyboard = [
            [InlineKeyboardButton("🎯 Рассчитать норму", callback_data="calculate")],
            [InlineKeyboardButton("💝 Поддержать бота", callback_data="donate")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем новое сообщение с историей
        await query.message.edit_text(message, reply_markup=reply_markup, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "state" not in context.user_data:
        await update.message.reply_text(
            get_main_menu_message(),
            reply_markup=get_main_menu_keyboard()
        )
        return
    try:
        if context.user_data["state"] == "weight":
            weight_text = update.message.text.replace(',', '.').encode('utf-8').decode('utf-8')
            weight = float(weight_text)
            if weight < 20 or weight > 300:
                raise ValueError("weight")
            context.user_data["weight"] = weight
            keyboard = [[InlineKeyboardButton("◀️ Назад к выбору пола", callback_data="back_to_gender")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"📏 Введи рост в см (например, {context.user_data.get('height_example', '170')}):",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            context.user_data["state"] = "height"
        elif context.user_data["state"] == "height":
            height = float(update.message.text.replace(',', '.'))
            if height < 100 or height > 250:
                raise ValueError("height")
            context.user_data["height"] = height
            keyboard = [[InlineKeyboardButton("◀️ Назад к весу", callback_data="back_to_weight")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "👤 Введи возраст (например, 25):",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            context.user_data["state"] = "age"
        elif context.user_data["state"] == "age":
            age = int(update.message.text)
            if age < 12 or age > 100:
                raise ValueError("age")
            context.user_data["age"] = age
            
            # Показываем клавиатуру активности только один раз
            keyboard = [
                [InlineKeyboardButton("Минимальная", callback_data="activity_min")],
                [InlineKeyboardButton("Низкая", callback_data="activity_low")],
                [InlineKeyboardButton("Средняя", callback_data="activity_medium")],
                [InlineKeyboardButton("Высокая", callback_data="activity_high")],
                [InlineKeyboardButton("Очень высокая", callback_data="activity_very_high")],
                [InlineKeyboardButton("◀️ Назад к возрасту", callback_data="back_to_age")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем новое сообщение с клавиатурой активности
            await update.message.reply_text(
                "🏃 Выбери уровень активности:\n\n"
                "• Минимальная - сидячий образ жизни\n"
                "• Низкая - легкие тренировки 1-2 раза в неделю\n"
                "• Средняя - умеренные тренировки 3-4 раз в неделю\n"
                "• Высокая - интенсивные тренировки 5-6 раз в неделю\n"
                "• Очень высокая - ежедневные интенсивные тренировки или физическая работа",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
            # Устанавливаем состояние активности
            context.user_data["state"] = "activity"
        elif context.user_data["state"] == "set_target":
            # 7. Исправить обработку установки цели по весу
            try:
                target_weight = float(update.message.text.replace(',', '.'))
                if target_weight < 20 or target_weight > 300:
                    raise ValueError("weight")
                user_id = update.effective_user.id
                set_target_weight(user_id, target_weight)
                await update.message.reply_text(
                    f"✅ Целевой вес ({target_weight} кг) успешно установлен!",
                    reply_markup=get_main_menu_keyboard()
                )
            except Exception as e:
                await update.message.reply_text(
                    "❌ Пожалуйста, введите корректный вес (от 20 до 300 кг):",
                    reply_markup=get_main_menu_keyboard()
                )
            context.user_data.pop("state", None)
            return
    except ValueError as e:
        error_message = {
            "weight": "Вес должен быть от 20 до 300 кг",
            "height": "Рост должен быть от 100 до 250 см",
            "age": "Возраст должен быть от 12 до 100 лет"
        }.get(str(e), str(e))
        await update.message.reply_text(
            f"❌ {error_message}",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
        context.user_data.pop("state", None)
        return
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка. Пожалуйста, попробуй снова.",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
        context.user_data.pop("state", None)
        return

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню"""
    query = update.callback_query
    await query.answer()
    
    last_calculation = context.user_data.get("last_calculation")
    reply_markup = get_main_menu_keyboard()
    message = get_main_menu_message(last_calculation)
    
    try:
        # Пробуем отредактировать существующее сообщение
        await query.message.edit_text(
            message,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error editing message in back_to_main: {e}")
        try:
            # Если не удалось отредактировать, отправляем новое сообщение
            await query.message.reply_text(
                message,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error sending new message: {e}")
    
    # Сбрасываем состояние пользователя
    context.user_data.pop("state", None)
    context.user_data.pop("current_vitamins_index", None)
    context.user_data.pop("current_nutrition_index", None)
    context.user_data.pop("current_seasonal_index", None)
    context.user_data.pop("current_diets_index", None)

async def back_to_tips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в меню полезных советов"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🌱 Сезонные продукты", callback_data="tips_seasonal")],
        [InlineKeyboardButton("📋 Таблички", callback_data="tips_tables")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        # Пробуем отредактировать существующее сообщение
        await query.message.edit_text(
            get_tips_menu_message(),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error editing message in back_to_tips: {e}")
        try:
            # Если не удалось отредактировать, отправляем новое сообщение
            await query.message.reply_text(
                get_tips_menu_message(),
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error sending new message: {e}")
    
    # Сбрасываем индексы карточек при возврате в меню
    context.user_data.pop("current_seasonal_index", None)
    context.user_data.pop("current_tables_index", None)

async def share_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("ℹ️ О боте", callback_data="about_bot")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем новое сообщение вместо редактирования
    await query.message.reply_text(
        "🤖 *Поделись ботом с друзьями!*\n\n"
        "Если бот помог тебе, поделись им с друзьями и близкими.\n"
        "Вместе мы сделаем мир здоровее! 💪\n\n"
        "[@norma_zhora_bot](https://t.me/norma_zhora_bot)",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def send_start_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет напоминание о команде /start при длительном простое"""
    keyboard = [
        [InlineKeyboardButton("🔄 Начать заново", callback_data="start_new")],
        [InlineKeyboardButton("❌ Закрыть", callback_data="close_reminder")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 Похоже, ты давно не пользовался ботом!\n\n"
        "Напиши /start или нажми кнопку ниже, чтобы начать заново.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_start_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Начать заново'"""
    query = update.callback_query
    await query.answer()
    await start(update, context)

async def handle_close_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки 'Закрыть' в напоминании"""
    query = update.callback_query
    await query.answer()
    await query.message.delete()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды помощи"""
    keyboard = [
        [InlineKeyboardButton("🔄 Начать заново", callback_data="start_new")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    help_text = (
        "🤖 *Как пользоваться ботом*\n\n"
        "Я помогу тебе рассчитать нормы питания и следить за здоровьем. Вот что я умею:\n\n"
        "📝 *Основные команды:*\n"
        "• /start - начать работу со мной\n"
        "• /help - показать это сообщение\n\n"
        "🎯 *Что я могу:*\n"
        "• Рассчитать твою норму калорий и БЖУ\n"
        "• Помочь следить за весом\n"
        "• Показать полезные советы по питанию\n"
        "• Рассказать о витаминах и диетах\n\n"
        "💡 *Совет:* Если ты потерялся в меню, просто напиши /start - это всегда вернет тебя в главное меню!"
    )
    
    if update.callback_query:
        await update.callback_query.message.edit_text(
            help_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            help_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("activity_keyboard_shown", None)
    keyboard = get_main_menu_keyboard()
    await update.message.reply_text(
        get_main_menu_message(),
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def show_tips_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню полезных советов"""
    keyboard = [
        [InlineKeyboardButton("📊 Трекеры", callback_data="tips_tables")],
        [InlineKeyboardButton("◀️ Назад в меню", callback_data=CALLBACK['MAIN_MENU'])]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=get_tips_menu_message(),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=get_tips_menu_message(),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

async def handle_card_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик навигации по карточкам"""
    query = update.callback_query
    await query.answer()
    
    # Получаем категорию из callback_data
    if query.data.startswith('card_next_') or query.data.startswith('card_prev_'):
        category = query.data.split('_')[-1]
    else:
        return
        
    cards = get_nutrition_cards(category=category)
    if not cards:
        await query.message.edit_text(
            f"❌ Карточки категории {category} не найдены",
            reply_markup=get_tips_menu_keyboard(),
            parse_mode="Markdown"
        )
        return
        
    # Получаем текущий индекс
    index_key = f"current_{category}_index"
    current_index = context.user_data.get(index_key, 0)
    
    # Обновляем индекс
    if query.data.startswith('card_next_'):
        if current_index < len(cards) - 1:
            current_index += 1
    elif query.data.startswith('card_prev_'):
        if current_index > 0:
            current_index -= 1
            
    # Сохраняем новый индекс
    context.user_data[index_key] = current_index
    
    # Получаем текущую карточку
    current_card = cards[current_index]
    caption = current_card[4] if len(current_card) > 4 and current_card[4] else ""
    
    # Создаем клавиатуру
    keyboard = [
        [InlineKeyboardButton("◀️", callback_data=f"card_prev_{category}")],
        [InlineKeyboardButton("▶️", callback_data=f"card_next_{category}")],
        [InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_tips")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await query.message.edit_text(
            caption,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error displaying card: {e}")
        await query.message.edit_text(
            "❌ Произошла ошибка при отображении карточки. Пожалуйста, попробуйте позже.",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

def get_seasonal_submenu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Весна", callback_data="season_spring")],
        [InlineKeyboardButton("Лето", callback_data="season_summer")],
        [InlineKeyboardButton("Осень", callback_data="season_autumn")],
        [InlineKeyboardButton("Зима", callback_data="season_winter")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_tips")]
    ])

def get_tables_submenu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_tips")]
    ])

def main():
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Добавляем обработчики команд и запросов от кнопок
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))  # Команда помощи
    application.add_handler(CommandHandler("stats", stats_command))  # Команда статистики для администратора
    # Удалена команда /weight
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^calculate$|^tips$|^share_bot$|^calc_self$|^calc_friend$|^set_target$|^back_to_weight$|^back_to_gender$|^back_to_age$"))
    application.add_handler(CallbackQueryHandler(handle_gender, pattern="^gender_"))
    application.add_handler(CallbackQueryHandler(handle_activity, pattern="^activity_"))
    # Удалены show_weight_history, handle_new_weight
    application.add_handler(CallbackQueryHandler(show_calculation_history, pattern="^calc_history$"))
    application.add_handler(CallbackQueryHandler(back_to_main, pattern="^back_to_main$"))
    application.add_handler(CallbackQueryHandler(back_to_tips, pattern="^back_to_tips$"))
    application.add_handler(CallbackQueryHandler(handle_card_navigation, pattern="^card_prev_|^card_next_"))
    application.add_handler(CallbackQueryHandler(about_bot, pattern="^about_bot$"))
    application.add_handler(CallbackQueryHandler(handle_donation, pattern="^donate$"))
    application.add_handler(CallbackQueryHandler(process_donation, pattern="^donate_\\d+$"))
    application.add_handler(CallbackQueryHandler(handle_stats_callback, pattern="^refresh_stats$|^stats_today$|^stats_week$"))  # Обработчики статистики
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    keep_alive()  # Запускаем keep_alive для поддержания активности
    main()