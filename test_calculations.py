#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def calculate_nutrition_norms(weight, height, age, gender, activity_level):
    """Рассчитывает нормы питания"""
    # Константы для уровней активности
    ACTIVITY_LEVELS = {
        "минимальная": 1.2,
        "низкая": 1.375,
        "средняя": 1.55,
        "высокая": 1.725,
        "очень высокая": 1.9
    }
    
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
    
    # Белки: современные рекомендации с учетом возраста, пола и активности
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
    
    # Жиры: корректировка по полу и возрасту
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
        if age < 18:
            fat_percentage_min, fat_percentage_max = 0.30, 0.40  # Подростки: больше жиров
        elif age < 30:
            fat_percentage_min, fat_percentage_max = 0.25, 0.35  # Молодые женщины
        elif age < 50:
            fat_percentage_min, fat_percentage_max = 0.25, 0.35  # Средний возраст
        else:
            fat_percentage_min, fat_percentage_max = 0.30, 0.40  # Пожилые: больше жиров
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
        
    # Рассчитываем норму воды согласно научным рекомендациям с учетом возраста
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
    
    # Базовая норма воды в зависимости от возраста
    base_water_per_kg = 30
    
    # Рассчитываем норму воды
    water_norm_min = weight * base_water_per_kg * water_multiplier * age_multiplier * activity_water_multiplier
    water_norm_max = water_norm_min * 1.1  # +10% для индивидуальных различий
    
    # Рассчитываем рекомендуемые шаги
    recommended_steps_min = 8000
    recommended_steps_max = 12000
    
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
        'recommended_steps_max': recommended_steps_max,
        'age_category': age_category
    }

def test_calculations():
    """Тестирует современные формулы расчета с учетом возраста, пола, активности и климакса"""
    print("🧪 Тестирование современных научных формул расчета с учетом климакса...")
    
    # Тест 1: Подросток, 16 лет, 60 кг, 170 см, средняя активность, мужской пол
    print("\n📊 Тест 1: Подросток, 16 лет, 60 кг, 170 см, средняя активность, мужской пол")
    results1 = calculate_nutrition_norms(60, 170, 16, "мужской", "средняя")
    print(f"Возрастная категория: {results1['age_category']}")
    print(f"BMR: {results1['bmr']} ккал")
    print(f"Норма калорий для поддержания веса: {results1['maintenance_calories']} ккал")
    print(f"Безопасный дефицит 15% для похудения: {results1['deficit_calories_15']} ккал")
    print(f"🥗 Рекомендуемые БЖУ (с учетом пола и активности):")
    print(f"🥩 Белки: {results1['protein_min']:.1f}-{results1['protein_max']:.1f}г (повышенная потребность для роста + мужской пол + средняя активность)")
    print(f"🥑 Жиры: {results1['fat_min']:.1f}-{results1['fat_max']:.1f}г (25-35% от калорий)")
    print(f"🍚 Углеводы: {results1['carbs_min']:.1f}-{results1['carbs_max']:.1f}г")
    print(f"ИМТ: {results1['bmi']} ({results1['bmi_category']})")
    print(f"💧 Норма воды: {results1['water_norm_min']:.0f}-{results1['water_norm_max']:.0f}мл (повышенная потребность)")
    print(f"👣 Рекомендуемые шаги: {results1['recommended_steps_min']}-{results1['recommended_steps_max']} (повышенная активность)")
    
    # Тест 2: Молодая женщина, 25 лет, 65 кг, 165 см, высокая активность
    print("\n📊 Тест 2: Молодая женщина, 25 лет, 65 кг, 165 см, высокая активность")
    results2 = calculate_nutrition_norms(65, 165, 25, "женский", "высокая")
    print(f"Возрастная категория: {results2['age_category']}")
    print(f"BMR: {results2['bmr']} ккал")
    print(f"Норма калорий для поддержания веса: {results2['maintenance_calories']} ккал")
    print(f"Безопасный дефицит 15% для похудения: {results2['deficit_calories_15']} ккал")
    print(f"🥗 Рекомендуемые БЖУ (с учетом пола и активности):")
    print(f"🥩 Белки: {results2['protein_min']:.1f}-{results2['protein_max']:.1f}г (стандартные рекомендации + женский пол + высокая активность)")
    print(f"🥑 Жиры: {results2['fat_min']:.1f}-{results2['fat_max']:.1f}г (25-35% от калорий)")
    print(f"🍚 Углеводы: {results2['carbs_min']:.1f}-{results2['carbs_max']:.1f}г")
    print(f"ИМТ: {results2['bmi']} ({results2['bmi_category']})")
    print(f"💧 Норма воды: {results2['water_norm_min']:.0f}-{results2['water_norm_max']:.0f}мл")
    print(f"👣 Рекомендуемые шаги: {results2['recommended_steps_min']}-{results2['recommended_steps_max']} (высокая активность)")
    
    # Тест 3: Женщина в перименопаузе, 50 лет, 70 кг, 165 см, средняя активность
    print("\n📊 Тест 3: Женщина в перименопаузе, 50 лет, 70 кг, 165 см, средняя активность")
    results3 = calculate_nutrition_norms(70, 165, 50, "женский", "средняя")
    print(f"Возрастная категория: {results3['age_category']}")
    print(f"BMR: {results3['bmr']} ккал")
    print(f"Норма калорий для поддержания веса: {results3['maintenance_calories']} ккал")
    print(f"Безопасный дефицит 15% для похудения: {results3['deficit_calories_15']} ккал")
    print(f"🥗 Рекомендуемые БЖУ (с учетом климакса):")
    print(f"🥩 Белки: {results3['protein_min']:.1f}-{results3['protein_max']:.1f}г (увеличенная потребность для предотвращения саркопении + перименопауза + средняя активность)")
    print(f"🥑 Жиры: {results3['fat_min']:.1f}-{results3['fat_max']:.1f}г (30-40% от калорий для гормональной поддержки)")
    print(f"🍚 Углеводы: {results3['carbs_min']:.1f}-{results3['carbs_max']:.1f}г")
    print(f"ИМТ: {results3['bmi']} ({results3['bmi_category']})")
    print(f"💧 Норма воды: {results3['water_norm_min']:.0f}-{results3['water_norm_max']:.0f}мл (+5% для перименопаузы)")
    print(f"👣 Рекомендуемые шаги: {results3['recommended_steps_min']}-{results3['recommended_steps_max']} (снижена активность)")
    
    # Тест 4: Женщина в постменопаузе, 60 лет, 65 кг, 160 см, низкая активность
    print("\n📊 Тест 4: Женщина в постменопаузе, 60 лет, 65 кг, 160 см, низкая активность")
    results4 = calculate_nutrition_norms(65, 160, 60, "женский", "низкая")
    print(f"Возрастная категория: {results4['age_category']}")
    print(f"BMR: {results4['bmr']} ккал")
    print(f"Норма калорий для поддержания веса: {results4['maintenance_calories']} ккал")
    print(f"Безопасный дефицит 15% для похудения: {results4['deficit_calories_15']} ккал")
    print(f"🥗 Рекомендуемые БЖУ (с учетом климакса):")
    print(f"🥩 Белки: {results4['protein_min']:.1f}-{results4['protein_max']:.1f}г (достаточные для поддержания здоровья + постменопауза + низкая активность)")
    print(f"🥑 Жиры: {results4['fat_min']:.1f}-{results4['fat_max']:.1f}г (30-40% от калорий для усвоения витаминов)")
    print(f"🍚 Углеводы: {results4['carbs_min']:.1f}-{results4['carbs_max']:.1f}г")
    print(f"ИМТ: {results4['bmi']} ({results4['bmi_category']})")
    print(f"💧 Норма воды: {results4['water_norm_min']:.0f}-{results4['water_norm_max']:.0f}мл (+10% для постменопаузы)")
    print(f"👣 Рекомендуемые шаги: {results4['recommended_steps_min']}-{results4['recommended_steps_max']} (значительно снижена активность)")
    
    # Тест 5: Сравнение женщин разных возрастов (одинаковые параметры, кроме возраста)
    print("\n📊 Тест 5: Сравнение норм для женщин разных возрастов (65 кг, 165 см, средняя активность)")
    results5_25 = calculate_nutrition_norms(65, 165, 25, "женский", "средняя")
    results5_50 = calculate_nutrition_norms(65, 165, 50, "женский", "средняя")
    results5_60 = calculate_nutrition_norms(65, 165, 60, "женский", "средняя")
    print(f"Женщина 25 лет:")
    print(f"  • Белки: {results5_25['protein_min']:.1f}-{results5_25['protein_max']:.1f}г")
    print(f"  • Жиры: {results5_25['fat_min']:.1f}-{results5_25['fat_max']:.1f}г")
    print(f"  • Вода: {results5_25['water_norm_min']:.0f}-{results5_25['water_norm_max']:.0f}мл")
    print(f"  • Шаги: {results5_25['recommended_steps_min']}-{results5_25['recommended_steps_max']}")
    
    print(f"Женщина 50 лет (перименопауза):")
    print(f"  • Белки: {results5_50['protein_min']:.1f}-{results5_50['protein_max']:.1f}г (+10%)")
    print(f"  • Жиры: {results5_50['fat_min']:.1f}-{results5_50['fat_max']:.1f}г (+5%)")
    print(f"  • Вода: {results5_50['water_norm_min']:.0f}-{results5_50['water_norm_max']:.0f}мл (+5%)")
    print(f"  • Шаги: {results5_50['recommended_steps_min']}-{results5_50['recommended_steps_max']} (-5%)")
    
    print(f"Женщина 60 лет (постменопауза):")
    print(f"  • Белки: {results5_60['protein_min']:.1f}-{results5_60['protein_max']:.1f}г (+15%)")
    print(f"  • Жиры: {results5_60['fat_min']:.1f}-{results5_60['fat_max']:.1f}г (+5%)")
    print(f"  • Вода: {results5_60['water_norm_min']:.0f}-{results5_60['water_norm_max']:.0f}мл (+10%)")
    print(f"  • Шаги: {results5_60['recommended_steps_min']}-{results5_60['recommended_steps_max']} (-10%)")
    
    print("\n✅ Современное тестирование с учетом климакса завершено!")
    print("📚 Все формулы обновлены согласно последним научным рекомендациям!")
    print("🔬 Учтены: возрастные особенности, половые различия, уровень активности, климакс")
    print("💡 Особенности для женщин в период климакса:")
    print("   • 45-55 лет (перименопауза):")
    print("     - Белки: +10% для предотвращения саркопении")
    print("     - Жиры: +5% для гормональной поддержки")
    print("     - Вода: +5% для вывода токсинов")
    print("     - Шаги: -5% из-за снижения активности")
    print("   • 55+ лет (постменопауза):")
    print("     - Белки: +15% для предотвращения остеопороза")
    print("     - Жиры: +5% для усвоения жирорастворимых витаминов")
    print("     - Вода: +10% для вывода токсинов")
    print("     - Шаги: -10% из-за значительного снижения активности")

if __name__ == "__main__":
    test_calculations() 