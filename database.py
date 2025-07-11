import sqlite3
from datetime import datetime
import os

def init_db():
    db_path = os.path.join(os.getcwd(), 'nutric.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Создаем таблицу для хранения веса
    c.execute('''CREATE TABLE IF NOT EXISTS weight_history
                 (user_id INTEGER,
                  weight REAL,
                  date TEXT DEFAULT (datetime('now', '+3 hours')),
                  PRIMARY KEY (user_id, date))''')

    # Создаем таблицу для хранения параметров пользователя
    c.execute('''CREATE TABLE IF NOT EXISTS user_params
                 (user_id INTEGER PRIMARY KEY,
                  height REAL,
                  age INTEGER,
                  gender TEXT,
                  activity_level TEXT,
                  target_weight REAL)''')

    # Создаем таблицу для хранения истории расчетов
    c.execute('''CREATE TABLE IF NOT EXISTS calculation_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  date TEXT DEFAULT (datetime('now', '+3 hours')),
                  weight REAL,
                  height REAL,
                  age INTEGER,
                  gender TEXT,
                  activity_level TEXT,
                  bmr INTEGER,
                  maintenance_calories INTEGER,
                  deficit_calories_15 INTEGER,
                  deficit_calories_20 INTEGER,
                  surplus_calories INTEGER,
                  protein_min INTEGER,
                  protein_max INTEGER,
                  fat_min INTEGER,
                  fat_max INTEGER,
                  carbs_min INTEGER,
                  carbs_max INTEGER,
                  bmi REAL,
                  bmi_category TEXT,
                  water_norm_min REAL,
                  water_norm_max REAL,
                  recommended_steps_min INTEGER,
                  recommended_steps_max INTEGER)''')

    # Создаем таблицу для карточек витаминов и питания
    c.execute('''CREATE TABLE IF NOT EXISTS nutrition_cards
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT,
                  image_url TEXT,
                  category TEXT,
                  created_at TEXT DEFAULT (datetime('now', '+3 hours')),
                  description TEXT)''')

    # Создаем таблицу для отслеживания пользователей
    c.execute('''CREATE TABLE IF NOT EXISTS user_stats
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  last_name TEXT,
                  first_seen TEXT DEFAULT (datetime('now', '+3 hours')),
                  last_seen TEXT DEFAULT (datetime('now', '+3 hours')),
                  total_calculations INTEGER DEFAULT 0,
                  total_weight_entries INTEGER DEFAULT 0,
                  is_active BOOLEAN DEFAULT 1)''')

    # Создаем таблицу для отслеживания действий пользователей
    c.execute('''CREATE TABLE IF NOT EXISTS user_actions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  action_type TEXT,
                  action_data TEXT,
                  timestamp TEXT DEFAULT (datetime('now', '+3 hours')))''')

    # Создаем таблицу для статистики по дням
    c.execute('''CREATE TABLE IF NOT EXISTS daily_stats
                 (date TEXT PRIMARY KEY,
                  new_users INTEGER DEFAULT 0,
                  active_users INTEGER DEFAULT 0,
                  total_calculations INTEGER DEFAULT 0,
                  total_weight_entries INTEGER DEFAULT 0,
                  donations_count INTEGER DEFAULT 0,
                  donations_amount REAL DEFAULT 0)''')

    conn.commit()
    conn.close()

    # Добавляем карточки с информацией
    add_vitamin_cards()
    add_seasonal_cards()
    add_nutrition_cards()
    add_diet_cards()

def save_weight(user_id, weight):
    db_path = os.path.join(os.getcwd(), 'nutric.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    try:
        c.execute('''INSERT INTO weight_history (user_id, weight, date)
                    VALUES (?, ?, datetime('now', '+3 hours'))''', (user_id, weight))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_weight_history(user_id, days=30):
    db_path = os.path.join(os.getcwd(), 'nutric.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    try:
        c.execute('''SELECT weight, date FROM weight_history 
                    WHERE user_id = ? 
                    AND date >= datetime('now', '-' || ? || ' days', '+3 hours')
                    ORDER BY date DESC''', (user_id, days))

        history = c.fetchall()
        for weight, date in history:
            date_obj = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
            yield weight, date_obj
    except Exception as e:
        return []
    finally:
        conn.close()

def save_user_params(user_id, weight, height, age, gender, target_weight=None):
    db_path = os.path.join(os.getcwd(), 'nutric.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    try:
        c.execute('''INSERT OR REPLACE INTO user_params 
                    (user_id, weight, height, age, gender, target_weight)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                 (user_id, weight, height, age, gender, target_weight))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_user_params(user_id):
    db_path = os.path.join(os.getcwd(), 'nutric.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    try:
        c.execute('SELECT weight, height, age, gender, target_weight FROM user_params WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        if result:
            return {
                'weight': result[0],
                'height': result[1],
                'age': result[2],
                'gender': result[3],
                'target_weight': result[4]
            }
        return None
    except Exception as e:
        return None
    finally:
        conn.close()

def save_calculation_results(user_id, results, params=None):
    db_path = os.path.join(os.getcwd(), 'nutric.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    try:
        weight = params.get('weight', 0) if params else 0
        height = params.get('height', 0) if params else 0
        age = params.get('age', 0) if params else 0
        gender = params.get('gender', '') if params else ''
        activity_level = params.get('activity_level', '') if params else ''
        
        print(f"Saving calculation for user {user_id}")
        print(f"Params: weight={weight}, height={height}, age={age}, gender={gender}, activity_level={activity_level}")
        print(f"Results keys: {list(results.keys())}")
        
        # Используем SQLite функцию для получения текущего времени в UTC+3 (Москва)
        c.execute('''INSERT INTO calculation_history 
                    (user_id, weight, height, age, gender, activity_level,
                     bmr, maintenance_calories, deficit_calories_15, 
                     deficit_calories_20, surplus_calories, protein_min, protein_max,
                     fat_min, fat_max, carbs_min, carbs_max, bmi, bmi_category,
                     water_norm_min, water_norm_max, recommended_steps_min, 
                     recommended_steps_max, date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', '+3 hours'))''',
                 (user_id, weight, height, age, gender, activity_level,
                  results['bmr'], results['maintenance_calories'],
                  results['deficit_calories_15'], results['deficit_calories_20'],
                  results['surplus_calories'], results['protein_min'],
                  results['protein_max'], results['fat_min'], results['fat_max'],
                  results['carbs_min'], results['carbs_max'], results['bmi'],
                  results['bmi_category'], results['water_norm_min'],
                  results['water_norm_max'], results.get('recommended_steps_min', 0),
                  results.get('recommended_steps_max', 0)))
        conn.commit()
        
        # Проверяем, какая дата была сохранена
        c.execute('SELECT date FROM calculation_history WHERE user_id = ? ORDER BY id DESC LIMIT 1', (user_id,))
        saved_date = c.fetchone()
        if saved_date:
            print(f"Saved date: {saved_date[0]}")
        
        print(f"Calculation saved successfully for user {user_id}")
    except Exception as e:
        conn.rollback()
        print(f"Error saving calculation for user {user_id}: {e}")
        raise e
    finally:
        conn.close()

def get_calculation_history(user_id, limit=5):
    db_path = os.path.join(os.getcwd(), 'nutric.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    try:
        c.execute('''SELECT * FROM calculation_history 
                    WHERE user_id = ? 
                    ORDER BY date DESC 
                    LIMIT ?''', (user_id, limit))
        rows = c.fetchall()
        
        # Получаем названия колонок
        columns = [description[0] for description in c.description]
        
        # Преобразуем кортежи в словари
        result = []
        for row in rows:
            calc_dict = dict(zip(columns, row))
            result.append(calc_dict)
        
        return result
    except Exception as e:
        return []
    finally:
        conn.close()

def get_last_calculation(user_id):
    db_path = os.path.join(os.getcwd(), 'nutric.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    try:
        c.execute('''SELECT * FROM calculation_history 
                    WHERE user_id = ? 
                    ORDER BY date DESC 
                    LIMIT 1''', (user_id,))
        row = c.fetchone()
        
        if row:
            # Получаем названия колонок
            columns = [description[0] for description in c.description]
            # Преобразуем кортеж в словарь
            return dict(zip(columns, row))
        return None
    except Exception as e:
        return None
    finally:
        conn.close()

def save_nutrition_card(title, image_url, category="vitamins", description=None):
    db_path = os.path.join(os.getcwd(), 'nutric.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    try:
        c.execute('''INSERT INTO nutrition_cards (title, image_url, category, description)
                    VALUES (?, ?, ?, ?)''', (title, image_url, category, description))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_nutrition_cards(category=None, limit=10):
    db_path = os.path.join(os.getcwd(), 'nutric.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    try:
        if category:
            c.execute('''SELECT * FROM nutrition_cards 
                        WHERE category = ? 
                        ORDER BY created_at DESC 
                        LIMIT ?''', (category, limit))
        else:
            c.execute('''SELECT * FROM nutrition_cards 
                        ORDER BY created_at DESC 
                        LIMIT ?''', (limit,))
        return c.fetchall()
    except Exception as e:
        return []
    finally:
        conn.close()

def clear_all_nutrition_cards():
    db_path = os.path.join(os.getcwd(), 'nutric.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    try:
        c.execute('DELETE FROM nutrition_cards')
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def add_vitamin_cards():
    conn = sqlite3.connect('nutric.db')
    c = conn.cursor()

    # Добавляем карточки с витаминами
    cards = [
        ('Витамин А', 'https://i.imgur.com/s5la750.png', 'vitamins',
         '🥕 *Витамин А (Ретинол)*\n\n'
         'Важный жирорастворимый витамин для здоровья:\n\n'
             '• Поддерживает зрение\n'
             '• Укрепляет иммунитет\n'
             '• Участвует в росте клеток\n'
             '• Поддерживает здоровье кожи\n\n'
         '💡 *Источники витамина А:*\n'
             '• Печень\n'
             '• Морковь\n'
         '• Сладкий картофель\n'
             '• Шпинат\n'
         '• Тыква\n\n'
         '💡 *Совет:* Витамин А лучше усваивается с жирами, поэтому добавляй в блюда немного масла.'),

        ('Витамин В1', 'https://i.imgur.com/A4PulpK.png', 'vitamins',
         '🌾 *Витамин В1 (Тиамин)*\n\n'
         'Водорастворимый витамин группы B:\n\n'
         '• Поддерживает работу нервной системы\n'
         '• Участвует в энергетическом обмене\n'
         '• Помогает работе сердца\n'
         '• Поддерживает пищеварение\n\n'
         '💡 *Источники витамина В1:*\n'
         '• Цельнозерновые крупы\n'
         '• Свинина\n'
         '• Орехи\n'
         '• Бобовые\n'
         '• Семена подсолнечника\n\n'
         '💡 *Совет:* Витамин В1 разрушается при высоких температурах, поэтому старайся готовить продукты щадящими методами.'),

        ('Витамин В2', 'https://i.imgur.com/placeholder.png', 'vitamins',
         '🥛 *Витамин В2 (Рибофлавин)*\n\n'
         'Водорастворимый витамин группы B:\n\n'
         '• Участвует в энергетическом обмене\n'
         '• Поддерживает здоровье кожи\n'
         '• Улучшает зрение\n'
         '• Участвует в образовании эритроцитов\n\n'
         '💡 *Источники витамина В2:*\n'
         '• Молочные продукты\n'
             '• Яйца\n'
         '• Мясо\n'
         '• Зеленые листовые овощи\n'
         '• Грибы\n\n'
         '💡 *Совет:* Витамин В2 чувствителен к свету, храни продукты в темном месте.'),

        ('Витамин В3', 'https://i.imgur.com/placeholder.png', 'vitamins',
         '🥩 *Витамин В3 (Ниацин)*\n\n'
         'Водорастворимый витамин группы B:\n\n'
         '• Участвует в энергетическом обмене\n'
         '• Поддерживает нервную систему\n'
         '• Улучшает состояние кожи\n'
         '• Регулирует уровень холестерина\n\n'
         '💡 *Источники витамина В3:*\n'
         '• Мясо и птица\n'
         '• Рыба\n'
         '• Цельнозерновые продукты\n'
         '• Бобовые\n'
         '• Орехи\n\n'
         '💡 *Совет:* Витамин В3 устойчив к нагреванию, но разрушается при длительном хранении.'),

        ('Витамин В5', 'https://i.imgur.com/placeholder.png', 'vitamins',
         '🥑 *Витамин В5 (Пантотеновая кислота)*\n\n'
         'Водорастворимый витамин группы B:\n\n'
         '• Участвует в синтезе гормонов\n'
         '• Поддерживает иммунитет\n'
         '• Участвует в энергетическом обмене\n'
         '• Помогает заживлению ран\n\n'
         '💡 *Источники витамина В5:*\n'
         '• Авокадо\n'
         '• Мясо и птица\n'
         '• Яйца\n'
         '• Бобовые\n'
         '• Цельнозерновые продукты\n\n'
         '💡 *Совет:* Витамин В5 разрушается при нагревании и замораживании.'),

        ('Витамин В6', 'https://i.imgur.com/qW7iXHz.png', 'vitamins',
         '🥩 *Витамин В6 (Пиридоксин)*\n\n'
         'Водорастворимый витамин группы B:\n\n'
         '• Участвует в обмене белков\n'
         '• Поддерживает нервную систему\n'
         '• Помогает образованию гемоглобина\n'
         '• Регулирует уровень гомоцистеина\n'
         '• Участвует в синтезе гормонов\n\n'
         '💡 *Источники витамина В6:*\n'
         '• Мясо и птица\n'
         '• Рыба (тунец, лосось)\n'
         '• Бананы\n'
         '• Картофель\n'
         '• Нут\n'
         '• Авокадо\n\n'
         '💡 *Совет:* Витамин В6 чувствителен к свету и нагреванию. Старайся готовить продукты щадящими методами.'),

        ('Витамин В7', 'https://i.imgur.com/placeholder.png', 'vitamins',
         '🥚 *Витамин В7 (Биотин)*\n\n'
         'Водорастворимый витамин группы B:\n\n'
         '• Поддерживает здоровье кожи и волос\n'
         '• Участвует в обмене веществ\n'
         '• Поддерживает нервную систему\n'
         '• Участвует в синтезе жирных кислот\n\n'
         '💡 *Источники витамина В7:*\n'
         '• Яичные желтки\n'
         '• Печень\n'
         '• Орехи\n'
         '• Бобовые\n'
         '• Цветная капуста\n\n'
         '💡 *Совет:* Биотин устойчив к нагреванию, но разрушается при длительном хранении.'),

        ('Витамин В9', 'https://i.imgur.com/v394ujX.png', 'vitamins',
         '🥬 *Витамин В9 (Фолиевая кислота)*\n\n'
         'Важный водорастворимый витамин:\n\n'
         '• Участвует в делении клеток\n'
         '• Поддерживает кроветворение\n'
         '• Важен для развития плода\n'
         '• Регулирует уровень гомоцистеина\n'
         '• Поддерживает иммунитет\n\n'
         '💡 *Источники витамина В9:*\n'
         '• Зеленые листовые овощи\n'
         '• Бобовые\n'
         '• Печень\n'
         '• Цитрусовые\n'
         '• Авокадо\n'
         '• Орехи и семена\n\n'
         '💡 *Совет:* Фолиевая кислота разрушается при длительной тепловой обработке. Употребляй овощи в свежем виде или минимально обработанными.'),

        ('Витамин В12', 'https://i.imgur.com/placeholder.png', 'vitamins',
         '🥩 *Витамин В12 (Кобаламин)*\n\n'
         'Водорастворимый витамин группы B:\n\n'
         '• Участвует в образовании эритроцитов\n'
         '• Поддерживает нервную систему\n'
         '• Участвует в синтезе ДНК\n'
         '• Поддерживает энергетический обмен\n\n'
         '💡 *Источники витамина В12:*\n'
         '• Мясо и рыба\n'
         '• Молочные продукты\n'
             '• Яйца\n'
         '• Морепродукты\n'
         '• Обогащенные продукты\n\n'
         '💡 *Совет:* Витамин В12 устойчив к нагреванию, но чувствителен к свету.'),

        ('Витамин С', 'https://i.imgur.com/z033ZB5.png', 'vitamins',
         '🍊 *Витамин С (Аскорбиновая кислота)*\n\n'
         'Мощный водорастворимый антиоксидант:\n\n'
         '• Укрепляет иммунитет\n'
         '• Участвует в синтезе коллагена\n'
         '• Помогает усвоению железа\n'
         '• Защищает от свободных радикалов\n'
         '• Ускоряет заживление ран\n\n'
         '💡 *Источники витамина С:*\n'
         '• Цитрусовые (апельсины, лимоны)\n'
         '• Киви\n'
         '• Болгарский перец\n'
         '• Брокколи\n'
         '• Черная смородина\n'
         '• Шиповник\n\n'
         '💡 *Совет:* Витамин С разрушается при нагревании и на свету. Старайся употреблять продукты в свежем виде и хранить их в темном прохладном месте.'),

        ('Витамин D', 'https://i.imgur.com/nEZvwzr.png', 'vitamins',
         '☀️ *Витамин D*\n\n'
         'Важный жирорастворимый витамин:\n\n'
         '• Укрепляет кости и зубы\n'
         '• Поддерживает иммунитет\n'
         '• Регулирует уровень кальция\n'
         '• Влияет на настроение\n\n'
         '💡 *Источники витамина D:*\n'
         '• Жирная рыба (лосось, скумбрия)\n'
         '• Яичные желтки\n'
         '• Грибы\n'
         '• Солнечный свет\n'
         '• Обогащенные продукты\n\n'
         '💡 *Совет:* В осенне-зимний период может потребоваться дополнительный прием витамина D.'),

        ('Витамин E', 'https://i.imgur.com/IfYneHt.png', 'vitamins',
         '🌰 *Витамин E (Токоферол)*\n\n'
         'Мощный антиоксидант:\n\n'
         '• Защищает клетки от повреждений\n'
         '• Поддерживает иммунитет\n'
         '• Улучшает состояние кожи\n'
         '• Поддерживает зрение\n\n'
         '💡 *Источники витамина E:*\n'
         '• Растительные масла\n'
         '• Орехи и семена\n'
         '• Авокадо\n'
         '• Шпинат\n'
         '• Брокколи\n\n'
         '💡 *Совет:* Витамин E лучше усваивается с жирами, добавляй в салаты растительное масло.'),

        ('Витамин K', 'https://i.imgur.com/87CZOsF.png', 'vitamins',
         '🥬 *Витамин K*\n\n'
         'Важный жирорастворимый витамин:\n\n'
         '• Участвует в свертывании крови\n'
         '• Поддерживает здоровье костей\n'
         '• Регулирует кальциевый обмен\n'
         '• Поддерживает здоровье сосудов\n\n'
         '💡 *Источники витамина K:*\n'
         '• Зеленые листовые овощи\n'
         '• Брокколи\n'
         '• Брюссельская капуста\n'
         '• Печень\n'
         '• Яйца\n\n'
         '💡 *Совет:* Витамин K устойчив к нагреванию, но разрушается на свету, храни продукты в темном месте.')
    ]

    for title, image_url, category, description in cards:
        c.execute('''INSERT INTO nutrition_cards 
                    (title, image_url, category, description)
                    VALUES (?, ?, ?, ?)''',
                 (title, image_url, category, description))

        conn.commit()
    conn.close()

def set_target_weight(user_id, target_weight):
    conn = sqlite3.connect('nutric.db')
    c = conn.cursor()
    c.execute('''UPDATE user_params 
                SET target_weight = ? 
                WHERE user_id = ?''', (target_weight, user_id))
    conn.commit()
    conn.close()

def add_seasonal_cards():
    conn = sqlite3.connect('nutric.db')
    c = conn.cursor()

    # Добавляем карточки с сезонными продуктами для июля
    cards = [
        ('Сезонные ягоды июля', 'https://i.imgur.com/aChYbBA.png', 'seasonal', 
         '🍓 *Сезонные ягоды июля*\n\n'
         '• *Малина*\n'
         '  - Лидер по содержанию витамина C\n'
         '  - Богата клетчаткой (6.5г на 100г)\n'
         '  - Содержит природное вещество, помогающее при простуде\n'
         '  - Помогает при простуде и температуре\n'
         '  - Улучшает пищеварение\n'
         '  - Содержит природные вещества, защищающие от болезней\n\n'
         '• *Черника*\n'
         '  - Богата антоцианами, улучшающими зрение\n'
         '  - Содержит витамины A, C, E\n'
         '  - Помогает при диарее\n'
         '  - Обладает противовоспалительными свойствами\n'
         '  - Улучшает память и когнитивные функции\n'
         '  - Содержит антиоксиданты\n\n'
         '• *Смородина*\n'
         '  - Богата витамином C\n'
         '  - Содержит витамины группы B\n'
         '  - Помогает при простуде\n'
         '  - Улучшает состояние кожи\n'
         '  - Обладает мочегонным эффектом\n'
         '  - Содержит пектин\n\n'
         '• *Крыжовник*\n'
         '  - Богат витамином C и клетчаткой\n'
         '  - Содержит калий и магний\n'
         '  - Помогает при запорах\n'
         '  - Улучшает пищеварение\n'
         '  - Обладает мочегонным эффектом\n'
         '  - Содержит фолиевую кислоту\n\n'
         '💡 *Советы по употреблению:*\n'
         '• Ягоды лучше есть в свежем виде\n'
         '• Хранить в холодильнике не более 2-3 дней\n'
         '• Для длительного хранения можно заморозить\n'
         '⚠️ *Противопоказания:*\n'
         '• При аллергии на ягоды\n'
         '• При обострении гастрита\n'
         '• При язвенной болезни\n'
         '• При сахарном диабете (в ограниченных количествах)'),

        ('Овощи июля', 'https://i.imgur.com/xf2cKxw.png', 'seasonal',
         '🥬 *Овощи июля*\n\n'
         'В июле созревают многие овощи:\n\n'
         '• *Помидоры*\n'
         '  - Богаты ликопином, защищающим от рака\n'
         '  - Содержат витамины A, C, E\n'
         '  - Помогают при сердечно-сосудистых заболеваниях\n'
         '  - Улучшают состояние кожи\n'
         '  - Содержат калий и магний\n'
         '  - Низкокалорийные (18 ккал на 100г)\n\n'
         '• *Огурцы*\n'
         '  - Богаты водой и клетчаткой\n'
         '  - Содержат витамины группы B\n'
         '  - Помогают при отеках\n'
         '  - Улучшают пищеварение\n'
         '  - Обладают мочегонным эффектом\n'
         '  - Содержат кремний\n\n'
         '• *Кабачки*\n'
         '  - Богаты калием и магнием\n'
         '  - Содержат витамины A, C, группы B\n'
         '  - Помогают при запорах\n'
         '  - Улучшают пищеварение\n'
         '  - Обладают мочегонным эффектом\n'
         '  - Низкокалорийные (17 ккал на 100г)\n\n'
         '• *Баклажаны*\n'
         '  - Богаты клетчаткой и калием\n'
         '  - Содержат витамины группы B\n'
         '  - Помогают снижать холестерин\n'
         '  - Улучшают работу сердца\n'
         '  - Содержат антиоксиданты\n'
         '  - Низкокалорийные (24 ккал на 100г)\n\n'
         '⚠️ *Противопоказания:*\n'
         '• При обострении гастрита и язвы\n'
         '• При заболеваниях поджелудочной железы\n'
         '• При индивидуальной непереносимости\n'
         '• При метеоризме'),

        ('Зелень июля', 'https://i.imgur.com/YNa2q02.png', 'seasonal',
         '🌿 *Свежая зелень июля*\n\n'
         'В июле особенно полезна свежая зелень:\n\n'
         '• *Укроп*\n'
         '  - Богат витамином C\n'
         '  - Содержит кальций и железо\n'
         '  - Помогает при метеоризме\n'
         '  - Обладает мочегонным эффектом\n'
         '  - Содержит полезные эфирные масла\n'
         '  - Улучшает пищеварение\n\n'
         '• *Петрушка*\n'
         '  - Лидер по содержанию витамина K\n'
         '  - Богата витамином C\n'
         '  - Содержит фолиевую кислоту\n'
         '  - Поддерживает здоровье костей\n'
         '  - Улучшает зрение\n'
         '  - Обладает противовоспалительными свойствами\n\n'
         '• *Базилик*\n'
         '  - Содержит полезные эфирные масла\n'
         '  - Богат витаминами A, K, C\n'
         '  - Обладает антибактериальными свойствами\n'
         '  - Помогает при стрессе\n'
         '  - Улучшает пищеварение\n'
         '  - Поддерживает иммунитет\n\n'
         '• *Шпинат*\n'
         '  - Содержит кальций и магний\n'
         '  - Богат витаминами A, C, K\n'
         '  - Содержит фолиевую кислоту\n'
         '  - Поддерживает здоровье глаз\n'
         '  - Содержит полезные вещества для зрения\n'
         '  - Низкокалорийный (23 ккал на 100г)\n\n'
         '💡 *Советы по употреблению:*\n'
         '• Добавляй свежую зелень в салаты\n'
         '• Используй как приправу к готовым блюдам\n'
         '• Храни в холодильнике в контейнере с водой\n'
         '• Можно замораживать для длительного хранения\n'
         '• Шпинат лучше есть в свежем виде или минимально обработанным\n\n'
         '⚠️ *Противопоказания:*\n'
         '• При мочекаменной болезни (ограничить шпинат)\n'
         '• При обострении гастрита\n'
         '• При индивидуальной непереносимости')
    ]

    for title, image_url, category, description in cards:
        c.execute('''INSERT INTO nutrition_cards 
                    (title, image_url, category, description)
                    VALUES (?, ?, ?, ?)''',
                 (title, image_url, category, description))

    conn.commit()
    conn.close()

def add_nutrition_cards():
    cards = [
            ('Белки', 'https://i.imgur.com/BiHW5dG.png', 'nutrition',
             '🥩 *Белки*\n\n'
             'Основной строительный материал организма:\n\n'
             '📋 *Функции:*\n'
             '• Строительный материал для мышц\n'
             '• Участвуют в синтезе гормонов\n'
             '• Поддерживают иммунитет\n'
             '• Транспортируют питательные вещества\n'
             '• Участвуют в обмене веществ\n\n'
             '💡 *Источники белка:*\n'
             '• Мясо и птица\n'
             '• Рыба и морепродукты\n'
             '• Яйца\n'
             '• Молочные продукты\n'
             '• Бобовые\n'
             '• Орехи и семена\n'
             '• Тофу и соевые продукты\n\n'
             '📊 *Нормы потребления:*\n'
             '• При наборе массы: 2-2.5г на 1 кг веса\n'
             '• При поддержании веса: 1.6-2г на 1 кг веса\n'
             '• При похудении: 1.8-2.2г на 1 кг веса\n\n'
             '⚠️ *Важно:*\n'
         '• Распределяй белок равномерно в течение дня\n'
         '• Сочетай животные и растительные источники\n'
         '• Учитывай биологическую ценность белка'),

        ('Жиры', 'https://i.imgur.com/1iWtn76.png', 'nutrition',
         '🥑 *Жиры*\n\n'
         'Важный источник энергии и питательных веществ:\n\n'
         '📋 *Типы жиров:*\n\n'
         '1. *Насыщенные жиры:*\n'
         '• Содержатся в: сливочном масле, сале, жирном мясе, кокосовом масле\n'
         '• Рекомендуется ограничивать до 10% от общего калоража\n'
         '• При избытке повышают уровень "плохого" холестерина\n\n'
         '2. *Мононенасыщенные жиры:*\n'
         '• Содержатся в: оливковом масле, авокадо, орехах (миндаль, фундук)\n'
         '• Помогают снижать "плохой" холестерин\n'
         '• Поддерживают здоровье сердца\n\n'
         '3. *Полиненасыщенные жиры:*\n'
         '• Омега-3: жирная рыба (лосось, скумбрия), льняное масло, грецкие орехи\n'
         '• Омега-6: подсолнечное масло, кукурузное масло, семена подсолнечника\n'
         '• Важны для работы мозга и сердца\n'
         '• Оптимальное соотношение Омега-3 к Омега-6: 1:4\n\n'
         '4. *Трансжиры:*\n'
         '• Содержатся в: маргарине, фастфуде, выпечке\n'
         '• Рекомендуется полностью исключить\n'
         '• Повышают риск сердечно-сосудистых заболеваний\n\n'
         '📊 *Нормы потребления:*\n'
         '• 20-35% от общего калоража\n'
         '• При похудении: 0.8-1г на 1 кг веса\n'
         '• При наборе массы: 1-1.5г на 1 кг веса\n\n'
         '⚠️ *Важно:*\n'
         '• Отдавай предпочтение полезным жирам\n'
         '• Ограничивай насыщенные жиры\n'
         '• Избегай трансжиров\n'
         '• Следи за балансом Омега-3 и Омега-6'),

        ('Углеводы', 'https://i.imgur.com/mukJnSS.png', 'nutrition',
         '🍚 *Углеводы*\n\n'
         'Основной источник энергии для организма:\n\n'
         '📋 *Типы углеводов:*\n\n'
         '1. *Простые углеводы:*\n'
         '• Моносахариды: глюкоза, фруктоза, галактоза\n'
         '• Дисахариды: сахароза, лактоза, мальтоза\n'
         '• Содержатся в: сахаре, меде, фруктах, молоке\n'
         '• Быстро усваиваются, резко повышают уровень сахара\n'
         '• Рекомендуется ограничивать\n\n'
         '2. *Сложные углеводы:*\n'
         '• Полисахариды: крахмал, гликоген, клетчатка\n'
         '• Содержатся в: цельнозерновых крупах, бобовых, овощах\n'
         '• Медленно усваиваются, дают длительное чувство сытости\n'
         '• Поддерживают стабильный уровень сахара\n\n'
         '3. *Клетчатка:*\n'
         '• Растворимая: овсянка, яблоки, цитрусовые\n'
         '• Нерастворимая: отруби, овощи, цельнозерновые\n'
         '• Норма: 25-30г в день\n'
         '• Поддерживает здоровье кишечника\n\n'
         '📊 *Нормы потребления:*\n'
         '• При наборе массы: 4-6г на 1 кг веса\n'
         '• При поддержании веса: 3-4г на 1 кг веса\n'
         '• При похудении: 2-3г на 1 кг веса\n\n'
         '⚠️ *Важно:*\n'
         '• Отдавай предпочтение сложным углеводам\n'
         '• Ограничивай простые углеводы\n'
         '• Учитывай гликемический индекс\n'
         '• Следи за достаточным потреблением клетчатки'),

        ('Основы правильного питания', 'https://ibb.co/7tBQwgBW', 'nutrition',
         '🥗 *Основы правильного питания*\n\n'
         '1. *Режим питания:*\n'
         '• 5-6 приемов пищи в день\n'
         '• Интервалы между приемами 2.5-3 часа\n'
         '• Последний прием за 2-3 часа до сна\n\n'
         '2. *Распределение БЖУ:*\n'
         '• Белки: 30-35% от калорий\n'
         '• Жиры: 25-30% от калорий\n'
         '• Углеводы: 35-45% от калорий\n\n'
         '3. *Питьевой режим:*\n'
         '• 30-40 мл воды на 1 кг веса\n'
         '• Пить за 30 минут до еды\n'
         '• Не пить во время еды\n'
         '• Пить через 1 час после еды\n\n'
         '4. *Правила приема пищи:*\n'
         '• Тщательно пережевывать\n'
         '• Не отвлекаться на гаджеты\n'
         '• Есть медленно и осознанно\n'
         '• Следить за размером порций'),

        ('Правильное питание для похудения', 'https://ibb.co/XZrBBcfZ', 'nutrition',
         '📉 *Правильное питание для похудения*\n\n'
         '1. *Основные принципы:*\n'
         '• Дефицит калорий 15-20%\n'
         '• Достаточное количество белка\n'
         '• Ограничение простых углеводов\n'
         '• Полезные жиры в рационе\n\n'
         '2. *Что исключить:*\n'
         '• Сахар и сладости\n'
         '• Мучные изделия\n'
         '• Фастфуд\n'
         '• Алкоголь\n'
         '• Сладкие напитки\n\n'
         '3. *Что включить:*\n'
         '• Овощи и зелень\n'
         '• Нежирное мясо и рыбу\n'
         '• Яйца и молочные продукты\n'
         '• Цельнозерновые крупы\n'
         '• Полезные жиры\n\n'
         '4. *Рекомендации:*\n'
         '• Вести дневник питания\n'
         '• Планировать меню заранее\n'
         '• Готовить еду дома\n'
         '• Не пропускать приемы пищи'),

        ('Правильное питание для набора массы', 'https://ibb.co/XZ96hRV0', 'nutrition',
         '📈 *Правильное питание для набора массы*\n\n'
         '1. *Основные принципы:*\n'
         '• Профицит калорий 10-15%\n'
         '• Повышенное количество белка\n'
         '• Достаточно углеводов\n'
         '• Полезные жиры\n\n'
         '2. *Распределение БЖУ:*\n'
         '• Белки: 2-2.5г на 1 кг веса\n'
         '• Жиры: 1-1.5г на 1 кг веса\n'
         '• Углеводы: 4-6г на 1 кг веса\n\n'
         '3. *Что включить:*\n'
         '• Сложные углеводы\n'
         '• Белковые продукты\n'
         '• Полезные жиры\n'
         '• Спортивное питание\n\n'
         '4. *Рекомендации:*\n'
         '• Есть каждые 2-3 часа\n'
         '• Пить достаточно воды\n'
         '• Следить за качеством пищи\n'
         '• Отдыхать и высыпаться')
    ]

    for card in cards:
        save_nutrition_card(*card)

def get_vitamin_cards():
    conn = sqlite3.connect('nutric.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, image_url, created_at, description
        FROM nutrition_cards
        WHERE category = 'vitamins'
        ORDER BY created_at DESC
    """)
    cards = cursor.fetchall()
    conn.close()
    return cards

def add_diet_cards():
    conn = sqlite3.connect('nutric.db')
    c = conn.cursor()

    # Добавляем карточки с диетами
    cards = [
        ('Средиземноморская диета', 'https://i.ibb.co/9mCjqbHR/mediterranean-diet.jpg', 'diets',
             '🌊 *Средиземноморская диета*\n\n'
         'Одна из самых здоровых и научно обоснованных диет в мире:\n\n'
             '📋 *Основные принципы:*\n'
             '• Оливковое масло как основной источник жиров\n'
             '• Овощи и фрукты (7-10 порций в день)\n'
             '• Цельнозерновые продукты\n'
             '• Бобовые и орехи\n'
             '• Рыба и морепродукты (2-3 раза в неделю)\n'
             '• Умеренное потребление молочных продуктов\n'
             '• Красное мясо редко (не чаще 1-2 раз в неделю)\n'
             '• Красное вино в умеренных количествах\n\n'
             '✅ *Польза:*\n'
         '• Снижение риска сердечно-сосудистых заболеваний\n'
         '• Профилактика диабета 2 типа\n'
         '• Поддержание здорового веса\n'
         '• Улучшение работы мозга\n'
         '• Продление жизни\n'
         '• Снижение воспалительных процессов\n\n'
             '⚠️ *Противопоказания:*\n'
             '• При аллергии на морепродукты\n'
         '• При непереносимости глютена\n'
         '• При заболеваниях печени (ограничить вино)\n'
         '• При обострении заболеваний ЖКТ\n\n'
         '💡 *Советы:*\n'
         '• Постепенно вводи новые продукты\n'
         '• Готовь на оливковом масле\n'
         '• Используй много свежих трав\n'
         '• Ешь медленно, наслаждаясь едой\n'
         '• Пей достаточно воды'),

        ('Кетогенная диета', 'https://i.ibb.co/KcvghZN9/ketogenic-diet.jpg', 'diets',
         '🥩 *Кетогенная диета*\n\n'
         'Диета с высоким содержанием жиров и низким содержанием углеводов, требующая строгого медицинского контроля:\n\n'
         '📋 *Основные принципы:*\n'
         '• 70-80% калорий из жиров\n'
         '• 20-25% калорий из белков\n'
         '• 5-10% калорий из углеводов (не более 50г в день)\n'
         '• Исключение сахара и крахмала\n'
         '• Умеренное потребление белка\n'
         '• Достаточное количество воды\n\n'
         '✅ *Польза:*\n'
         '• Эффективна при эпилепсии (под контролем врача)\n'
         '• Снижение уровня сахара в крови\n'
         '• Улучшение концентрации внимания\n'
         '• Снижение чувства голода\n'
         '• Повышение энергии\n'
         '• Уменьшение воспалений\n\n'
         '⚠️ *Важные предостережения:*\n'
         '• Требуется строгий медицинский контроль\n'
         '• Необходимо регулярное обследование\n'
         '• Противопоказана при заболеваниях печени и почек\n'
         '• Противопоказана при диабете 1 типа\n'
         '• Противопоказана при панкреатите\n'
         '• Противопоказана при беременности и кормлении\n'
         '• Противопоказана при заболеваниях щитовидной железы\n\n'
         '💡 *Советы:*\n'
         '• Начинай только под наблюдением врача\n'
         '• Регулярно контролируйте показатели крови\n'
         '• Следи за электролитами\n'
         '• Пей больше воды\n'
         '• Веди дневник питания\n'
         '• При любых отклонениях консультируйся с врачом'),

        ('Интервальное голодание', 'https://i.ibb.co/r91HwxM/intermittent-fasting.jpg', 'diets',
         '🕒 *Интервальное голодание*\n\n'
         'Популярный подход к питанию, основанный на чередовании периодов приема пищи и голодания.\n\n'
         '📋 *Основные схемы:*\n'
         '• 16/8 - 16 часов голодания, 8 часов приема пищи\n'
         '• 14/10 - 14 часов голодания, 10 часов приема пищи\n'
         '• 5:2 - 5 дней обычного питания, 2 дня ограничения до 500-600 ккал\n\n'
         '✅ *Преимущества:*\n'
         '• Улучшение чувствительности к инсулину\n'
         '• Снижение воспалительных процессов\n'
         '• Возможное улучшение работы мозга\n'
         '• Удобство планирования питания\n\n'
         '⚠️ *Противопоказания:*\n'
         '• Сахарный диабет 1 и 2 типа\n'
         '• Заболевания щитовидной железы\n'
         '• Беременность и кормление грудью\n'
         '• Расстройства пищевого поведения\n'
         '• Заболевания ЖКТ (гастрит, язва)\n'
         '• Пониженное давление\n'
         '• Истощение и недостаточный вес\n'
         '• Детский и подростковый возраст\n'
         '• Период восстановления после операций\n'
         '• Хронические заболевания в стадии обострения\n\n'
         '💡 *Советы:*\n'
         '• Начинай постепенно\n'
         '• Следе за самочувствием\n'
         '• Пей достаточно воды\n'
         '• Выбирай качественные продукты в период приема пищи'),

        ('Вегетарианская диета', 'https://i.ibb.co/wh7cfWWX/vegetarian-diet.jpg', 'diets',
         '🥗 *Вегетарианская диета*\n\n'
         'Сбалансированный подход к питанию без мяса и рыбы:\n\n'
         '📋 *Основные принципы:*\n'
         '• Исключение мяса и рыбы\n'
         '• Упор на растительные белки\n'
         '• Молочные продукты и яйца разрешены\n'
         '• Большое количество овощей и фруктов\n'
         '• Цельнозерновые продукты\n'
         '• Бобовые и орехи\n\n'
         '✅ *Польза:*\n'
         '• Снижение риска сердечных заболеваний\n'
         '• Нормализация давления\n'
         '• Снижение уровня холестерина\n'
         '• Профилактика диабета 2 типа\n'
         '• Улучшение пищеварения\n'
         '• Экологичность\n\n'
         '⚠️ *Противопоказания:*\n'
         '• При анемии (требуется контроль железа)\n'
         '• При дефиците B12\n'
         '• При беременности (требуется консультация)\n'
         '• При активном росте у детей\n\n'
         '💡 *Советы:*\n'
         '• Следи за балансом белков\n'
         '• Принимай B12 дополнительно\n'
         '• Включай источники железа\n'
         '• Разнообразь рацион\n'
         '• Контролируй уровень витаминов'),

        ('Японская диета', 'https://i.ibb.co/rK44BfLR/japanese-diet.jpg', 'diets',
         '🍱 *Японская диета*\n\n'
         'Традиционный подход к питанию, основанный на балансе и умеренности:\n\n'
         '📋 *Основные принципы:*\n'
         '• Рис как основа рациона\n'
         '• Рыба и морепродукты\n'
         '• Овощи и водоросли\n'
         '• Ферментированные продукты\n'
         '• Маленькие порции\n'
         '• Медленное питание\n'
         '• Разнообразие блюд\n\n'
         '✅ *Польза:*\n'
         '• Долголетие\n'
         '• Поддержание здорового веса\n'
         '• Снижение риска сердечных заболеваний\n'
         '• Улучшение пищеварения\n'
         '• Антиоксидантный эффект\n'
         '• Баланс питательных веществ\n\n'
         '⚠️ *Противопоказания:*\n'
         '• При аллергии на морепродукты\n'
         '• При заболеваниях щитовидной железы\n'
         '• При непереносимости глютена\n'
         '• При заболеваниях ЖКТ\n\n'
         '💡 *Советы:*\n'
         '• Используй маленькие тарелки\n'
         '• Ешь медленно\n'
         '• Включай ферментированные продукты\n'
         '• Готовьтна пару\n'
         '• Следи за балансом')
    ]

    for title, image_url, category, description in cards:
        c.execute('''INSERT INTO nutrition_cards 
                    (title, image_url, category, description)
                    VALUES (?, ?, ?, ?)''',
                 (title, image_url, category, description))

    conn.commit()
    conn.close()

def get_target_weight(user_id):
    conn = sqlite3.connect('nutric.db')
    c = conn.cursor()
    c.execute('SELECT target_weight FROM user_params WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def track_user_action(user_id, action_type, action_data=None):
    db_path = os.path.join(os.getcwd(), 'nutric.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    try:
        c.execute('''INSERT INTO user_actions (user_id, action_type, action_data)
                    VALUES (?, ?, ?)''', (user_id, action_type, action_data))
        
        c.execute('''INSERT OR REPLACE INTO user_stats 
                    (user_id, last_seen, is_active) 
                    VALUES (?, datetime('now', '+3 hours'), 1)''', (user_id,))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def register_user(user_id, username=None, first_name=None, last_name=None):
    db_path = os.path.join(os.getcwd(), 'nutric.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    try:
        c.execute('''INSERT OR IGNORE INTO user_stats 
                    (user_id, username, first_name, last_name, first_seen, last_seen)
                    VALUES (?, ?, ?, ?, datetime('now', '+3 hours'), datetime('now', '+3 hours'))''',
                 (user_id, username, first_name, last_name))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_user_statistics():
    db_path = os.path.join(os.getcwd(), 'nutric.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    try:
        c.execute('SELECT COUNT(*) FROM user_stats')
        total_users = c.fetchone()[0]
        
        c.execute('''SELECT COUNT(*) FROM user_stats 
                    WHERE last_seen >= datetime('now', '-7 days', '+3 hours')''')
        active_users_7d = c.fetchone()[0]
        
        c.execute('''SELECT COUNT(*) FROM user_stats 
                    WHERE last_seen >= datetime('now', '-30 days', '+3 hours')''')
        active_users_30d = c.fetchone()[0]
        
        c.execute('''SELECT COUNT(*) FROM user_stats 
                    WHERE first_seen >= datetime('now', 'start of day', '+3 hours')''')
        new_users_today = c.fetchone()[0]
        
        c.execute('''SELECT COUNT(*) FROM user_stats 
                    WHERE first_seen >= datetime('now', '-7 days', '+3 hours')''')
        new_users_week = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM calculation_history')
        total_calculations = c.fetchone()[0]
        
        c.execute('''SELECT COUNT(*) FROM calculation_history 
                    WHERE date >= datetime('now', 'start of day', '+3 hours')''')
        calculations_today = c.fetchone()[0]
        
        c.execute('''SELECT COUNT(*) FROM calculation_history 
                    WHERE date >= datetime('now', '-7 days', '+3 hours')''')
        calculations_week = c.fetchone()[0]
        
        c.execute('''SELECT gender, COUNT(*) FROM calculation_history 
                    WHERE gender IS NOT NULL 
                    GROUP BY gender''')
        gender_stats = dict(c.fetchall())
        
        c.execute('''SELECT AVG(age) FROM calculation_history 
                    WHERE age IS NOT NULL AND age > 0''')
        avg_age = c.fetchone()[0]
        
        c.execute('''SELECT activity_level, COUNT(*) FROM calculation_history 
                    WHERE activity_level IS NOT NULL 
                    GROUP BY activity_level''')
        activity_stats = dict(c.fetchall())
        
        return {
            'total_users': total_users,
            'active_users_7d': active_users_7d,
            'active_users_30d': active_users_30d,
            'new_users_today': new_users_today,
            'new_users_week': new_users_week,
            'total_calculations': total_calculations,
            'calculations_today': calculations_today,
            'calculations_week': calculations_week,
            'gender_stats': gender_stats,
            'avg_age': round(avg_age, 1) if avg_age else 0,
            'activity_stats': activity_stats
        }
    except Exception as e:
        return {}
    finally:
        conn.close()

def get_popular_actions(days=7):
    db_path = os.path.join(os.getcwd(), 'nutric.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    try:
        c.execute('''SELECT action_type, COUNT(*) as count 
                    FROM user_actions 
                    WHERE timestamp >= datetime('now', '-{} days', '+3 hours')
                    GROUP BY action_type 
                    ORDER BY count DESC'''.format(days))
        
        actions = c.fetchall()
        return {action: count for action, count in actions}
    except Exception as e:
        return {}
    finally:
        conn.close()

def get_daily_stats(date=None):
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    db_path = os.path.join(os.getcwd(), 'nutric.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    try:
        c.execute('''SELECT COUNT(*) FROM user_stats 
                    WHERE first_seen >= datetime(?, 'start of day', '+3 hours')
                    AND first_seen < datetime(?, '+1 day', '+3 hours')''', (date, date))
        new_users = c.fetchone()[0]
        
        c.execute('''SELECT COUNT(DISTINCT user_id) FROM user_actions 
                    WHERE timestamp >= datetime(?, 'start of day', '+3 hours')
                    AND timestamp < datetime(?, '+1 day', '+3 hours')''', (date, date))
        active_users = c.fetchone()[0]
        
        c.execute('''SELECT COUNT(*) FROM calculation_history 
                    WHERE date >= datetime(?, 'start of day', '+3 hours')
                    AND date < datetime(?, '+1 day', '+3 hours')''', (date, date))
        calculations = c.fetchone()[0]
        
        c.execute('''SELECT COUNT(*) FROM weight_history 
                    WHERE date >= datetime(?, 'start of day', '+3 hours')
                    AND date < datetime(?, '+1 day', '+3 hours')''', (date, date))
        weight_entries = c.fetchone()[0]
        
        return {
            'date': date,
            'new_users': new_users,
            'active_users': active_users,
            'calculations': calculations,
            'weight_entries': weight_entries
        }
    except Exception as e:
        return {}
    finally:
        conn.close()

def format_statistics_message(stats):
    if not stats:
        return "❌ Не удалось получить статистику"
    
    message = "📊 *Статистика бота*\n\n"
    
    message += "👥 *Пользователи:*\n"
    message += f"• Всего пользователей: {stats.get('total_users', 0)}\n"
    message += f"• Активных за 7 дней: {stats.get('active_users_7d', 0)}\n"
    message += f"• Активных за 30 дней: {stats.get('active_users_30d', 0)}\n"
    message += f"• Новых сегодня: {stats.get('new_users_today', 0)}\n"
    message += f"• Новых за неделю: {stats.get('new_users_week', 0)}\n\n"
    
    message += "🎯 *Расчеты:*\n"
    message += f"• Всего расчетов: {stats.get('total_calculations', 0)}\n"
    message += f"• Расчетов сегодня: {stats.get('calculations_today', 0)}\n"
    message += f"• Расчетов за неделю: {stats.get('calculations_week', 0)}\n\n"
    
    if stats.get('gender_stats'):
        message += "👤 *По полу:*\n"
        for gender, count in stats['gender_stats'].items():
            gender_emoji = "👨" if gender == "мужской" else "👩"
            message += f"• {gender_emoji} {gender}: {count}\n"
        message += "\n"
    
    if stats.get('avg_age', 0) > 0:
        message += f"📅 *Средний возраст:* {stats['avg_age']} лет\n\n"
    
    if stats.get('activity_stats'):
        message += "🏃 *По активности:*\n"
        for activity, count in stats['activity_stats'].items():
            message += f"• {activity}: {count}\n"
        message += "\n"
    
    return message