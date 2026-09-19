import os
from database import ScadaDatabase

def parse_and_import_scada_log(log_file_path, db_name="scada_analytics.db"):
    """
    Функция считывает файл промышленной выгрузки логов, 
    разбирает каждую строку по элементам и загружает в SQLite.
    """
    # 1. Проверяем физическое наличие файла на диске перед открытием
    if not os.path.exists(log_file_path):
        print(f"[ОШИБКА ПАРСЕРА]: Файл '{log_file_path}' не найден.")
        return False

    # Инициализируем подключение к нашей базе данных
    db = ScadaDatabase(db_name)
    
    inserted_count = 0
    skipped_count = 0

    print(f"[ПАРСЕР]: Начало обработки файла выгрузки: {log_file_path}")

    # 2. Безопасное чтение файла с фиксацией контекста (контекстный менеджер with)
    with open(log_file_path, mode='r', encoding='utf-8') as file:
        for line_num, line in enumerate(file, start=1):
            # Удаляем символы переноса строк и лишние пробелы по краям
            clean_line = line.strip()
            
            # Игнорируем пустые строки в конце файла
            if not clean_line:
                continue
                
            # 3. Разбираем строку по разделителю (запятая)
            parts = clean_line.split(',')
            
            # Строка лога должна содержать строго 6 элементов
            if len(parts) != 6:
                print(f"[ПРЕДУПРЕЖДЕНИЕ]: Строка {line_num} повреждена (неверное число элементов). Пропуск.")
                skipped_count += 1
                continue
                
            try:
                # Очищаем каждый элемент от скрытых пробелов внутри кавычек/границ
                timestamp     = parts[0].strip()
                unit_name     = parts[1].strip()
                parameter     = parts[2].strip()
                current_val   = float(parts[3].strip())   # Приведение к числу с плавающей точкой
                critical_val  = float(parts[4].strip())   # Приведение к числу с плавающей точкой
                status        = parts[5].strip().upper()  # Приводим к верхнему регистру для стандартизации (INFO/WARNING/CRITICAL)
                
                # 4. Передаем структурированные данные в метод нашей БД
                db.add_log_entry(
                    timestamp=timestamp,
                    unit_name=unit_name,
                    parameter=parameter,
                    current_value=current_val,
                    critical_value=critical_val,
                    status=status
                )
                inserted_count += 1
                
            except ValueError as e:
                # Защита от падения, если вместо числа в значении датчика пришел текст (например, "ERR" или "NaN")
                print(f"[ОШИБКА СТРОКИ {line_num}]: Не удалось преобразовать числовые параметры датчиков. Пропуск. Текст ошибки: {e}")
                skipped_count += 1
                continue

    # Фиксируем изменения и закрываем соединение
    db.close()
    
    print("==================================================")
    print(f"[ПАРСЕР]: Обработка лога завершена успешно.")
    print(f" - Загружено валидных инцидентов: {inserted_count}")
    print(f" - Пропущено ошибочных строк: {skipped_count}")
    print("==================================================")
    return True

# Блок для автономного тестирования модуля парсинга
if __name__ == "__main__":
    # Для теста создадим рядом временный файл с вашей структурой выгрузки
    test_filename = "test_export.log"
    test_data = (
        "2026-09-01 08:00:15, ГПА-10-01, Температура подшипника компрессора, 72.4, 85.0, INFO\n"
        "2026-09-01 08:01:22, ГПА-10-01, Давление газа на входе, 4.1, 3.5, WARNING\n"
        "2026-09-01 08:02:05, ГПА-10-02, Вибрация турбины, 11.2, 10.0, CRITICAL\n"
    )
    
    with open(test_filename, "w", encoding="utf-8") as f:
        f.write(test_data)
        
    # Запускаем парсинг тестового файла
    parse_and_import_scada_log(test_filename)
    
    # Очищаем за собой тестовый текстовый файл
    if os.path.exists(test_filename):
        os.remove(test_filename)
