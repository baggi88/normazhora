#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from database import init_db, save_calculation_results, get_calculation_history

def test_database():
    print("Testing database functionality...")
    
    # Инициализируем базу данных
    init_db()
    print("Database initialized")
    
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
        save_calculation_results(user_id, results, params)
        print("Test calculation saved successfully")
    except Exception as e:
        print(f"Error saving calculation: {e}")
        return
    
    # Получаем историю расчетов
    try:
        history = get_calculation_history(user_id)
        print(f"Found {len(history)} calculations in history")
        
        if history:
            latest = history[0]
            print(f"Latest calculation date: {latest['date']}")
            print(f"Latest calculation weight: {latest['weight']} kg")
            print(f"Latest calculation BMR: {latest['bmr']} kcal")
        else:
            print("No calculations found in history")
            
    except Exception as e:
        print(f"Error getting history: {e}")

if __name__ == "__main__":
    test_database() 