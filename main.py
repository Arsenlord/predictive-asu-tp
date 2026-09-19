import sys
from datetime import datetime

# Импортируем компоненты графического движка PySide6
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QLabel, QLineEdit,
    QComboBox, QMessageBox, QHeaderView, QFrame, QGroupBox, QGridLayout
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

# Импортируем наш рабочий класс базы данных
from database import ScadaDatabase

class IndustrialStatsWidget(QWidget):
    """Виджет верхней панели KPI-показателей надежности оборудования"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        
        # Создаем карточки технологического контроля
        self.lbl_total    = self.create_card("Всего логов", "0", 0, 0, "#2196F3")
        self.lbl_info     = self.create_card("Режим INFO", "0", 0, 1, "#4CAF50")
        self.lbl_warning  = self.create_card("Предупреждения (WARN)", "0", 0, 2, "#FF9800")
        self.lbl_critical = self.create_card("Критические сбои", "0", 0, 3, "#F44336")
        
    def create_card(self, title, val, row, col, hex_color):
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{ background-color: {hex_color}; color: white; border-radius: 6px; padding: 12px; }}
            QLabel {{ color: white; background: transparent; }}
        """)
        v_box = QVBoxLayout(frame)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 11px; font-weight: bold; text-transform: uppercase;")
        v_box.addWidget(title_lbl)
        
        val_lbl = QLabel(val)
        val_lbl.setStyleSheet("font-size: 26px; font-weight: bold;")
        val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        v_box.addWidget(val_lbl)
        
        self.layout().addWidget(frame, row, col)
        return val_lbl

    def update_metrics(self, metrics):
        self.lbl_total.setText(str(metrics['total']))
        self.lbl_info.setText(str(metrics['info']))
        self.lbl_warning.setText(str(metrics['warning']))
        self.lbl_critical.setText(str(metrics['critical']))


class TodoApp(QMainWindow):
    """Главный диспетчерский пульт управления предиктивным мониторингом"""
    
    def __init__(self):
        super().__init__()
        self.db = ScadaDatabase("scada_analytics.db")
        self.current_unit = "Все"
        self.current_status = "Все"
        
        self.init_ui()
        self.refresh_data() # Вызывается строго ПОСЛЕ создания self.table в init_ui!
        
    def init_ui(self):
        self.setWindowTitle("Программно-технический комплекс предиктивного мониторинга инцидентов АСУ ТП")
        self.setMinimumSize(1200, 750)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 1. Подключаем верхние карточки KPI
        self.kpi_panel = IndustrialStatsWidget()
        main_layout.addWidget(self.kpi_panel)
        
        # 2. Панель инструментов и управления
        self.create_toolbar(main_layout)
        
        # 3. Интерактивная таблица логов
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Время события", "Технологический узел", "Контролируемый параметр", 
            "Значение", "Уставка (Предел)", "Статус"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        main_layout.addWidget(self.table)
    def create_toolbar(self, parent_layout):
        """Создание верхней панели инструментов"""
        toolbar = QHBoxLayout()
        
        self.btn_analyze = QPushButton("⚡ Запустить предиктивный анализ")
        self.btn_analyze.setMinimumHeight(35)
        self.btn_analyze.setStyleSheet("background-color: #E65100; color: white; font-weight: bold;")
        self.btn_analyze.clicked.connect(self.run_predictive_analysis)
        toolbar.addWidget(self.btn_analyze)
        
        self.btn_export = QPushButton("📋 Экспорт отчета в TXT")
        self.btn_export.setMinimumHeight(35)
        self.btn_export.setStyleSheet("background-color: #0D47A1; color: white; font-weight: bold;")
        self.btn_export.clicked.connect(self.export_analytical_report)
        toolbar.addWidget(self.btn_export)
        
        toolbar.addStretch()
        
        toolbar.addWidget(QLabel("Узел:"))
        self.combo_unit = QComboBox()
        self.combo_unit.addItems(["Все", "ГПА-10-01", "ГПА-10-02"])
        self.combo_unit.currentTextChanged.connect(self.filter_changed)
        toolbar.addWidget(self.combo_unit)
        
        toolbar.addWidget(QLabel("Критичность:"))
        self.combo_status = QComboBox()
        self.combo_status.addItems(["Все", "INFO", "WARNING", "CRITICAL"])
        self.combo_status.currentTextChanged.connect(self.filter_changed)
        toolbar.addWidget(self.combo_status)
        
        parent_layout.addLayout(toolbar)
        
    def refresh_data(self):
        logs = self.db.get_filtered_logs(self.current_unit, self.current_status)
        self.table.setRowCount(len(logs))
        
        for row_idx, log in enumerate(logs):
            for col_idx, val in enumerate(log[1:]):
                item = QTableWidgetItem(str(val))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                
                status_str = str(log[6]).upper() if len(log) > 6 else ""
                if status_str == "CRITICAL":
                    item.setForeground(QColor("#D32F2F"))
                    item.setFont(QFont("Segoe UI", 10, QFont.Bold))
                elif status_str == "WARNING":
                    item.setForeground(QColor("#E65100"))
                    
                self.table.setItem(row_idx, col_idx, item)
                
        metrics = self.db.get_analytics_metrics()
        self.kpi_panel.update_metrics(metrics)
        
    def filter_changed(self):
        self.current_unit = self.combo_unit.currentText()
        self.current_status = self.combo_status.currentText()
        self.refresh_data()
        
    def run_predictive_analysis(self):
        """Кнопка запуска алгоритма предиктивного анализа каскадных отказов"""
        # Выполняем расчет один раз и кэшируем результат в переменную класса
        self.last_alerts = self.db.detect_cascading_failures(time_window_seconds=300)
        
        if self.last_alerts:
            for alert in self.last_alerts:
                QMessageBox.critical(
                    self, 
                    "КРИТИЧЕСКАЯ УГРОЗА АВАРИИ!", 
                    f"Узел: {alert['unit_name']}\n"
                    f"Интервал развития сбоя: {alert['start_time']} -> {alert['end_time']}\n\n"
                    f"Аналитика АСУ ТП: {alert['details']}\n\n"
                    f"Рекомендация: Немедленно проверить систему ПАЗ, оповестить начальника смены и направить дежурного слесаря по КИПиА!"
                )
                break
        else:
            QMessageBox.information(
                self, "Анализ завершен", 
                "Каскадных сбоев и аномалий в плотности ошибок не обнаружено.\nОборудование работает штатно."
            )

    def export_analytical_report(self):
        """Функция генерации и сохранения аналитического рапорта на диск"""
        from PySide6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить аналитический отчет",
            f"АСУ_ТП_Рапорт_Безопасности_{datetime.now().strftime('%Y%m%d')}.txt",
            "Текстовые файлы (*.txt)"
        )
        
        if not file_path:
            return
            
        metrics = self.db.get_analytics_metrics()
        
        # ОПТИМИЗАЦИЯ (DRY): Вместо повторного тяжелого запроса к БД используем кэш.
        # Если пользователь не нажимал кнопку анализа ранее, рассчитываем на лету.
        alerts = getattr(self, 'last_alerts', None)
        if alerts is None:
            alerts = self.db.detect_cascading_failures(time_window_seconds=300)
        
        report_text = [
            "===================================================================",
            "             РАПОРТ ТЕХНИЧЕСКОГО СОСТОЯНИЯ И БЕЗОПАСНОСТИ          ",
            "                    СЛУЖБЫ АСУ ТП / ПРЕДИКТИВНЫЙ МОНИТОРИНГ        ",
            "===================================================================",
            f" Дата формирования: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f" Всего событий зафиксировано в смене: {metrics['total']}",
            "-------------------------------------------------------------------",
            " СТАТИСТИКА ПО КАТЕГОРИЯМ ТЕХНОЛОГИЧЕСКИХ ЛОГОВ:",
            f"  - Нормальный режим работы (INFO): {metrics['info']}",
            f"  - Предупредительные уставки (WARNING): {metrics['warning']}",
            f"  - Аварийные отклонения параметров (CRITICAL): {metrics['critical']}",
            "-------------------------------------------------------------------"
        ]
        
        if alerts:
            report_text.extend([
                " !!! ВНИМАНИЕ: АЛГОРИТМОМ ПРЕДИКТИВНОГО АНАЛИЗА ВЫЯВЛЕНЫ УГРОЗЫ !!!",
                " АНАЛИЗ КАСКАДНЫХ СБОЕВ ОБОРУДОВАНИЯ (Критерий: 3+ CRITICAL за 5 мин):"
            ])
            for alert in alerts:
                report_text.extend([
                    f"\n  [УЗЕЛ]: {alert['unit_name']}",
                    f"  [ВРЕМЯ РАЗВИТИЯ СБОЯ]: {alert['start_time']} -> {alert['end_time']} (Время: {alert['time_delta']} сек.)",
                    "  [ЦЕПОЧКА ЗАРЕГИСТРИРОВАННЫХ ИНЦИДЕНТОВ]:"
                ])
                for idx, ev in enumerate(alert['raw_events'], start=1):
                    report_text.append(f"    {idx}. [{ev['time_str']}] {ev['param']}: Факт: {ev['val']} (Уставка: {ev['crit']})")
                report_text.append("  [ЗАКЛЮЧЕНИЕ СИСТЕМЫ]: Каскадный отказ узла. Риск останова по ПАЗ 100%.")
        else:
            report_text.extend([
                " ЗАКЛЮЧЕНИЕ ПО ТЕХНОЛОГИЧЕСКОМУ ПРОЦЕССУ:",
                "  Каскадных сбоев и опасных аномалий плотности ошибок не обнаружено.",
                "  Динамическое и статическое оборудование работает в штатном режиме."
            ])
            
        report_text.extend([
            "-------------------------------------------------------------------",
            "\n\n Ответственный за предиктивный мониторинг:",
            " Ведущий инженер по АСУП ___________________ / А.И. Акчиу /",
            "\n Дежурный слесарь по КИПиА _________________",
            "==================================================================="
        ])
        
        try:
            with open(file_path, mode='w', encoding='utf-8') as file:
                file.write("\n".join(report_text))
            QMessageBox.information(self, "Экспорт успешен", f"Рапорт успешно записан в файл:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", f"Не удалось сохранить рапорт. Текст ошибки: {e}")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    window = TodoApp()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()

