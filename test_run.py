import os
from database import ScadaDatabase
from log_parser import parse_and_import_scada_log

def main():
    log_filename = "scada_export.log"
    db_filename = "scada_analytics.db"
    
    # Очищаем старую БД перед тестом, если она есть
    if os.path.exists(db_filename):
        os.remove(db_filename)
        
    print("[ТЕСТ]: Шаг 1. Импорт реальной выгрузки в базу данных...")
    # Запускаем ваш парсер
    success = parse_and_import_scada_log(log_filename, db_filename)
    
    if success:
        print("\n[ТЕСТ]: Шаг 2. Запуск алгоритма предиктивного анализа...")
        db = ScadaDatabase(db_filename)
        
        # Вызываем метод поиска каскадных аварий (интервал 300 секунд)
        cascading_alerts = db.detect_cascading_failures(time_window_seconds=300)
        
        print("\n================ РЕЗУЛЬТАТ АНАЛИЗА АСУ ТП ================")
        if cascading_alerts:
            for alert in cascading_alerts:
                print(f"⚠️ ОБНАРУЖЕНА УГРОЗА АВАРИИ!")
                print(f" - Технологический узел: {alert['unit_name']}")
                print(f" - Интервал развития сбоя: {alert['start_time']} ---> {alert['end_time']}")
                print(f" - Подробности: {alert['details']}")
        else:
            print("✅ Каскадных сбоев не обнаружено. Оборудование работает в рамках технологического регламента.")
        print("==========================================================")
        
        db.close()

if __name__ == "__main__":
    main()
