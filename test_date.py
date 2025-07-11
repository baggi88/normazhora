#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from datetime import datetime
import os

def test_date_saving():
    print("Testing date saving and reading...")
    
    # Создаем временную базу данных
    db_path = 'test_nutric.db'
    
    # Удаляем старую базу если есть
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Создаем таблицу
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
    
    # Тестовые данные
    user_id = 12345
    results = {
        'bmr': 1500,
        'maintenance_calories': 1800,
        'deficit_calories_15': 1530,
        'deficit_calories_20': 1440,
        'surplus_calories': 1980,
        'protein_min': 120,
        'protein_max': 150,
        'fat_min': 40,
        'fat_max': 60,
        'carbs_min': 180,
        'carbs_max': 220,
        'bmi': 22.5,
        'bmi_category': 'Нормальный вес',
        'water_norm_min': 2000,
        'water_norm_max': 2500,
        'recommended_steps_min': 8000,
        'recommended_steps_max': 10000
    }
    
    params = {
        'weight': 70,
        'height': 175,
        'age': 30,
        'gender': 'мужской',
        'activity_level': 'средняя'
    }
    
    # Сохраняем тестовый расчет
    try:
        c.execute('''INSERT INTO calculation_history 
                    (user_id, weight, height, age, gender, activity_level,
                     bmr, maintenance_calories, deficit_calories_15, 
                     deficit_calories_20, surplus_calories, protein_min, protein_max,
                     fat_min, fat_max, carbs_min, carbs_max, bmi, bmi_category,
                     water_norm_min, water_norm_max, recommended_steps_min, 
                     recommended_steps_max, date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', '+3 hours'))''',
                 (user_id, params['weight'], params['height'], params['age'], 
                  params['gender'], params['activity_level'],
                  results['bmr'], results['maintenance_calories'],
                  results['deficit_calories_15'], results['deficit_calories_20'],
                  results['surplus_calories'], results['protein_min'],
                  results['protein_max'], results['fat_min'], results['fat_max'],
                  results['carbs_min'], results['carbs_max'], results['bmi'],
                  results['bmi_category'], results['water_norm_min'],
                  results['water_norm_max'], results.get('recommended_steps_min', 0),
                  results.get('recommended_steps_max', 0)))
        conn.commit()
        print("Test calculation saved successfully")
        
        # Проверяем, какая дата была сохранена
        c.execute('SELECT date FROM calculation_history WHERE user_id = ? ORDER BY id DESC LIMIT 1', (user_id,))
        saved_date = c.fetchone()
        if saved_date:
            print(f"Saved date: {saved_date[0]}")
            
            # Пробуем распарсить дату
            try:
                date_obj = datetime.strptime(saved_date[0], "%Y-%m-%d %H:%M:%S")
                formatted_date = date_obj.strftime("%d.%m.%Y")
                print(f"Formatted date: {formatted_date}")
            except Exception as e:
                print(f"Error parsing date: {e}")
        
    except Exception as e:
        print(f"Error saving calculation: {e}")
        return
    
    conn.close()
    
    # Удаляем тестовую базу
    if os.path.exists(db_path):
        os.remove(db_path)

if __name__ == "__main__":
    test_date_saving() 