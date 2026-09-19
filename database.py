import sqlite3
import os
from datetime import datetime

class ScadaDatabase:
    def __init__(self, db_name="scada_analytics.db"):
        """Инициализация подключения к БД и создание структуры таблиц"""
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """Создание таблицы промышленных логов АСУ ТП и индексов"""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS scada_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                unit_name TEXT NOT NULL,
                parameter TEXT NOT NULL,
                current_value REAL NOT NULL,
                critical_value REAL NOT NULL,
                status TEXT NOT NULL
            )
        ''')
        
        # Создаем индекс по времени и имени узла для ускорения поиска
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp_unit 
            ON scada_logs (timestamp, unit_name)
        ''')
        self.conn.commit()

    def add_log_entry(self, timestamp, unit_name, parameter, current_value, critical_value, status):
        """Добавление одной записи технологического события в БД"""
        self.cursor.execute('''
            INSERT INTO scada_logs (timestamp, unit_name, parameter, current_value, critical_value, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (timestamp, unit_name, parameter, float(current_value), float(critical_value), status))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_filtered_logs(self, unit_filter="Все", status_filter="Все", search_term=""):
        """Выгрузка логов с динамической фильтрацией для таблицы PySide6"""
        query = "SELECT id, timestamp, unit_name, parameter, current_value, critical_value, status FROM scada_logs WHERE 1=1"
        params = []

        if unit_filter != "Все":
            query += " AND unit_name = ?"
            params.append(unit_filter)

        if status_filter != "Все":
            query += " AND status = ?"
            params.append(status_filter)

        if search_term:
            query += " AND (parameter LIKE ? OR unit_name LIKE ?)"
            params.append(f"%{search_term}%")
            params.append(f"%{search_term}%")

        query += " ORDER BY timestamp DESC"
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def get_analytics_metrics(self):
        """Расчет показателей KPI для карточек верхнего меню"""
        self.cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'INFO' THEN 1 ELSE 0 END) as info_count,
                SUM(CASE WHEN status = 'WARNING' THEN 1 ELSE 0 END) as warn_count,
                SUM(CASE WHEN status = 'CRITICAL' THEN 1 ELSE 0 END) as crit_count
            FROM scada_logs
        ''')
        row = self.cursor.fetchone()
        
        if row and row[0] is not None:
            return {
                'total': row[0],
                'info': row[1] if row[1] else 0,
                'warning': row[2] if row[2] else 0,
                'critical': row[3] if row[3] else 0
            }
        return {'total': 0, 'info': 0, 'warning': 0, 'critical': 0}

    def detect_cascading_failures(self, time_window_seconds=300):
        """Алгоритм предиктивного анализа каскадных сбоев"""
        self.cursor.execute('''
            SELECT unit_name, timestamp, parameter, current_value, critical_value 
            FROM scada_logs 
            WHERE status = 'CRITICAL'
            ORDER BY unit_name, timestamp ASC
        ''')
        rows = self.cursor.fetchall()

        units_events = {}
        for row in rows:
            unit_name, timestamp_str, param, val, crit = row
            if unit_name not in units_events:
                units_events[unit_name] = []
            units_events[unit_name].append({
                'time': datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S'),
                'time_str': timestamp_str,
                'param': param,
                'val': val,
                'crit': crit
            })

        alerts = []

        for unit_name, events in units_events.items():
            if len(events) < 3:
                continue

            for i in range(len(events) - 2):
                time_delta = (events[i+2]['time'] - events[i]['time']).total_seconds()

                if time_delta <= time_window_seconds:
                    raw_events = [events[i], events[i+1], events[i+2]]
                    alerts.append({
                        'unit_name': unit_name,
                        'start_time': events[i]['time_str'],
                        'end_time': events[i+2]['time_str'],
                        'time_delta': int(time_delta),
                        'raw_events': raw_events,
                        'details': f"Зафиксировано 3 критических отказа за {int(time_delta)} сек. Последний сбой: {events[i+2]['param']} ({events[i+2]['val']} при уставке {events[i+2]['crit']})"
                    })
                    break 

        return alerts

    def close(self):
        """Безопасное закрытие сессии СУБД"""
        self.conn.close()
