import sys
import json
import os
import re
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QFrame, QLineEdit, QDialog,
    QDialogButtonBox, QTextEdit, QMessageBox, QSizePolicy, QMenu,
    QTabWidget, QInputDialog
)
from PyQt6.QtCore import Qt, QMimeData, QPoint, pyqtSignal
from PyQt6.QtGui import QDrag, QPixmap, QPainter, QColor, QFont, QCursor

BOARDS_DIR = "boards"
DEFAULT_BOARD = "Моя доска"

DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 13px;
}
QLabel#TitleLabel {
    color: #89b4fa;
    font-size: 22px;
    font-weight: bold;
    padding: 8px;
}
QLabel#ColumnTitle {
    color: #f5e0dc;
    font-size: 15px;
    font-weight: bold;
    padding: 6px;
}
QLabel#CountBadge {
    background-color: #45475a;
    color: #cdd6f4;
    border-radius: 10px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: bold;
}
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #45475a;
    border-color: #89b4fa;
}
QPushButton:pressed {
    background-color: #585b70;
}
QPushButton#AddBtn {
    background-color: #89b4fa;
    color: #1e1e2e;
    font-weight: bold;
}
QPushButton#AddBtn:hover {
    background-color: #b4befe;
}
QPushButton#DeleteBtn {
    background-color: transparent;
    color: #f38ba8;
    border: none;
    padding: 2px 6px;
    font-size: 14px;
}
QPushButton#DeleteBtn:hover {
    color: #eba0ac;
    background-color: #45475a;
    border-radius: 4px;
}
QFrame#Column {
    background-color: #181825;
    border-radius: 10px;
    border: 1px solid #313244;
}
QFrame#TaskCard {
    background-color: #313244;
    border-radius: 8px;
    border-left: 4px solid #89b4fa;
}
QFrame#TaskCard:hover {
    background-color: #45475a;
}
QLabel#TaskTitle {
    color: #cdd6f4;
    font-weight: 600;
    font-size: 13px;
}
QLabel#TaskDesc {
    color: #a6adc8;
    font-size: 11px;
}
QScrollArea {
    background-color: transparent;
    border: none;
}
QScrollBar:vertical {
    background: #181825;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #45475a;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #585b70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QLineEdit, QTextEdit {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #89b4fa;
}
QMenu {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 20px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #45475a;
}
QDialog {
    background-color: #1e1e2e;
}
QTabWidget::pane {
    border: 1px solid #313244;
    border-radius: 8px;
    background-color: #1e1e2e;
    top: -1px;
}
QTabBar::tab {
    background-color: #313244;
    color: #a6adc8;
    border: 1px solid #313244;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 8px 18px;
    margin-right: 3px;
    font-weight: 500;
}
QTabBar::tab:selected {
    background-color: #1e1e2e;
    color: #89b4fa;
    border-bottom: 2px solid #89b4fa;
}
QTabBar::tab:hover:!selected {
    background-color: #45475a;
    color: #cdd6f4;
}
"""


def safe_filename(name: str) -> str:
    """Преобразует имя доски в безопасное имя файла."""
    name = name.strip().lower()
    name = re.sub(r"[^\w\-а-яё]+", "_", name, flags=re.IGNORECASE)
    return name.strip("_") or "board"


class TaskDialog(QDialog):
    def __init__(self, parent=None, title="", description=""):
        super().__init__(parent)
        self.setWindowTitle("Задача")
        self.setMinimumWidth(400)
        self.setStyleSheet(DARK_STYLE)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Название:"))
        self.title_edit = QLineEdit(title)
        self.title_edit.setPlaceholderText("Например: Сверстать лендинг")
        layout.addWidget(self.title_edit)

        layout.addWidget(QLabel("Описание:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlainText(description)
        self.desc_edit.setPlaceholderText("Дополнительные детали...")
        self.desc_edit.setFixedHeight(100)
        layout.addWidget(self.desc_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        return self.title_edit.text().strip(), self.desc_edit.toPlainText().strip()


class TaskCard(QFrame):
    delete_requested = pyqtSignal(object)
    edit_requested = pyqtSignal(object)

    def __init__(self, title, description, parent_column, parent=None):
        super().__init__(parent)
        self.title = title
        self.description = description
        self.parent_column = parent_column
        self.drag_start_pos = QPoint()

        self.setObjectName("TaskCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 8, 8, 8)
        self.main_layout.setSpacing(4)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("TaskTitle")
        self.title_label.setWordWrap(True)
        header.addWidget(self.title_label, 1)

        delete_btn = QPushButton("✕")
        delete_btn.setObjectName("DeleteBtn")
        delete_btn.setFixedSize(22, 22)
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(self))
        header.addWidget(delete_btn)

        self.main_layout.addLayout(header)

        # Сохраняем ссылку на описание, чтобы можно было его менять
        self.desc_label = QLabel(description)
        self.desc_label.setObjectName("TaskDesc")
        self.desc_label.setWordWrap(True)
        self.main_layout.addWidget(self.desc_label)
        if not description:
            self.desc_label.hide()

    def update_content(self, new_title, new_description):
        """Обновляет данные на карточке без её пересоздания."""
        self.title = new_title
        self.description = new_description
        self.title_label.setText(new_title)

        if new_description:
            self.desc_label.setText(new_description)
            self.desc_label.show()
        else:
            self.desc_label.hide()

    def show_context_menu(self, pos):
        menu = QMenu(self)
        edit_action = menu.addAction("✏  Редактировать")
        delete_action = menu.addAction("🗑  Удалить")
        action = menu.exec(self.mapToGlobal(pos))
        if action == edit_action:
            self.edit_requested.emit(self)
        elif action == delete_action:
            self.delete_requested.emit(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.position().toPoint() - self.drag_start_pos).manhattanLength() < 10:
            return

        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(self.title)

        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor("#45475a"))
        painter.setPen(QColor("#89b4fa"))
        painter.drawRoundedRect(pixmap.rect().adjusted(1, 1, -1, -1), 8, 8)
        painter.setPen(QColor("#cdd6f4"))
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(
            pixmap.rect().adjusted(12, 0, -12, 0),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self.title,
        )
        painter.end()

        drag.setMimeData(mime)
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.position().toPoint())
        drag.exec(Qt.DropAction.MoveAction)


class Column(QFrame):
    def __init__(self, title, color="#89b4fa", parent=None):
        super().__init__(parent)
        self.title = title
        self.color = color
        self.setObjectName("Column")
        self.setAcceptDrops(True)
        self.setMinimumWidth(280)
        self.setMaximumWidth(340)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        header = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("ColumnTitle")
        title_label.setStyleSheet(f"color: {color};")
        header.addWidget(title_label)

        self.count_label = QLabel("0")
        self.count_label.setObjectName("CountBadge")
        header.addWidget(self.count_label)
        header.addStretch()
        main_layout.addLayout(header)

        self.tasks_widget = QWidget()
        self.tasks_layout = QVBoxLayout(self.tasks_widget)
        self.tasks_layout.setContentsMargins(0, 0, 0, 0)
        self.tasks_layout.setSpacing(6)
        self.tasks_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.tasks_widget)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        main_layout.addWidget(scroll, 1)

        add_btn = QPushButton("＋  Добавить задачу")
        add_btn.setObjectName("AddBtn")
        add_btn.clicked.connect(self.add_task_dialog)
        main_layout.addWidget(add_btn)

    def add_task_widget(self, card: TaskCard):
        card.delete_requested.connect(self.remove_task)
        card.edit_requested.connect(self.edit_task)
        self.tasks_layout.insertWidget(self.tasks_layout.count() - 1, card)
        self.update_count()

    def add_task_dialog(self):
        dialog = TaskDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            title, desc = dialog.get_data()
            if title:
                card = TaskCard(title, desc, self)
                self.add_task_widget(card)
                self.notify_change()

    def remove_task(self, card: TaskCard):
        self.tasks_layout.removeWidget(card)
        card.deleteLater()
        self.update_count()
        self.notify_change()

    def edit_task(self, card: TaskCard):
        dialog = TaskDialog(self, card.title, card.description)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            title, desc = dialog.get_data()
            if title:
                # Обновляем данные в памяти
                card.title = title
                card.description = desc
                # Обновляем визуально на экране
                card.title_label.setText(title)
                card.desc_label.setText(desc)
                if desc:
                    card.desc_label.show()
                else:
                    card.desc_label.hide()
                # Сохраняем изменения
                self.notify_change()

    def update_count(self):
        count = sum(
            1 for i in range(self.tasks_layout.count())
            if isinstance(self.tasks_layout.itemAt(i).widget(), TaskCard)
        )
        self.count_label.setText(str(count))

    def notify_change(self):
        """Уведомить доску об изменении → автосохранение."""
        board = self.window()
        if hasattr(board, "save_data"):
            board.save_data()

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self.setStyleSheet(
                f"QFrame#Column {{ background-color: #1e1e2e; border: 1px solid {self.color}; }}"
            )

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")

    def dropEvent(self, event):
        self.setStyleSheet("")
        source = event.source()
        if isinstance(source, TaskCard):
            if source.parent_column is not self:
                old_column = source.parent_column
                old_column.tasks_layout.removeWidget(source)
                source.setParent(None)
                source.parent_column = self
                self.add_task_widget(source)
                old_column.update_count()
                self.notify_change()
            event.acceptProposedAction()


class BoardWidget(QWidget):
    """Одна доска — это отдельная вкладка."""

    def __init__(self, board_name, parent=None):
        super().__init__(parent)
        self.board_name = board_name

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        top_bar = QHBoxLayout()
        title = QLabel(f"📋  {board_name}")
        title.setObjectName("TitleLabel")
        top_bar.addWidget(title)
        top_bar.addStretch()

        clear_btn = QPushButton("🗑  Очистить доску")
        clear_btn.clicked.connect(self.clear_board)
        top_bar.addWidget(clear_btn)

        reset_btn = QPushButton("🔄  Сброс")
        reset_btn.clicked.connect(self.reset_board)
        top_bar.addWidget(reset_btn)

        layout.addLayout(top_bar)

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(12)
        layout.addLayout(columns_layout, 1)

        self.columns = {}
        for key, col_title, color in [
            ("todo", "📝  To Do", "#89b4fa"),
            ("in_progress", "⚙️  In Progress", "#fab387"),
            ("review", "👀  Review", "#cba6f7"),
            ("done", "✅  Done", "#a6e3a1"),
        ]:
            col = Column(col_title, color)
            self.columns[key] = col
            columns_layout.addWidget(col)

    # --- Файл ---
    def file_path(self):
        return os.path.join(BOARDS_DIR, safe_filename(self.board_name) + ".json")

    def load_data(self):
        path = self.file_path()
        if not os.path.exists(path):
            self.load_demo_data()
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key, tasks in data.items():
                if key in self.columns:
                    for task in tasks:
                        card = TaskCard(
                            task.get("title", ""),
                            task.get("description", ""),
                            self.columns[key],
                        )
                        self.columns[key].add_task_widget(card)
        except Exception as e:
            print(f"Ошибка загрузки {path}: {e}")

    def load_demo_data(self):
        demo = {
            "todo": [
                {"title": "Пример задачи", "description": "Перетащи меня в другую колонку →"},
            ],
            "in_progress": [],
            "review": [],
            "done": [],
        }
        for key, tasks in demo.items():
            for task in tasks:
                card = TaskCard(task["title"], task["description"], self.columns[key])
                self.columns[key].add_task_widget(card)
        self.save_data()

    def save_data(self):
        data = {}
        for key, col in self.columns.items():
            tasks = []
            for i in range(col.tasks_layout.count()):
                w = col.tasks_layout.itemAt(i).widget()
                if isinstance(w, TaskCard):
                    tasks.append({"title": w.title, "description": w.description})
            data[key] = tasks
        try:
            os.makedirs(BOARDS_DIR, exist_ok=True)
            with open(self.file_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения: {e}")

    def rename_to(self, new_name):
        """Переименование доски с пересохранением файла."""
        old_path = self.file_path()
        self.board_name = new_name
        new_path = self.file_path()
        try:
            if os.path.exists(old_path) and old_path != new_path:
                os.replace(old_path, new_path)
        except Exception as e:
            print(f"Не удалось переименовать файл: {e}")
        self.save_data()

    def clear_board(self):
        reply = QMessageBox.question(
            self, "Очистить доску",
            f"Удалить все задачи на доске «{self.board_name}»?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            for col in self.columns.values():
                for i in reversed(range(col.tasks_layout.count())):
                    w = col.tasks_layout.itemAt(i).widget()
                    if isinstance(w, TaskCard):
                        col.tasks_layout.removeWidget(w)
                        w.deleteLater()
                col.update_count()
            self.save_data()

    def reset_board(self):
        reply = QMessageBox.question(
            self, "Сброс доски",
            "Загрузить демо-данные? Текущие задачи будут заменены.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            for col in self.columns.values():
                for i in reversed(range(col.tasks_layout.count())):
                    w = col.tasks_layout.itemAt(i).widget()
                    if isinstance(w, TaskCard):
                        col.tasks_layout.removeWidget(w)
                        w.deleteLater()
                col.update_count()
            self.load_demo_data()


class KanbanWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kanban Board — Мультидоски")
        self.resize(1400, 800)
        self.setStyleSheet(DARK_STYLE)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(8, 8, 8, 8)

        top = QHBoxLayout()
        title = QLabel("📋  Канбан-доски")
        title.setObjectName("TitleLabel")
        top.addWidget(title)
        top.addStretch()

        new_board_btn = QPushButton("＋  Новая доска")
        new_board_btn.setObjectName("AddBtn")
        new_board_btn.clicked.connect(self.create_new_board_dialog)
        top.addWidget(new_board_btn)
        layout.addLayout(top)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(False)
        self.tabs.setMovable(True)
        self.tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self.tab_context_menu)
        self.tabs.tabBarDoubleClicked.connect(self.rename_tab_dialog)
        layout.addWidget(self.tabs, 1)

        self.load_existing_boards()

        if self.tabs.count() == 0:
            self.create_new_board(DEFAULT_BOARD)

    def load_existing_boards(self):
        if not os.path.isdir(BOARDS_DIR):
            return
        for fname in sorted(os.listdir(BOARDS_DIR)):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(BOARDS_DIR, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    json.load(f)
            except Exception:
                continue
            name = fname[:-5].replace("_", " ").title()
            self.create_new_board(name, auto_load=True)

    def create_new_board_dialog(self):
        name, ok = QInputDialog.getText(
            self, "Новая доска", "Название доски:", text="Новая доска"
        )
        if ok and name.strip():
            self.create_new_board(name.strip())

    def create_new_board(self, name, auto_load=True):
        base = name
        i = 1
        existing = [self.tabs.tabText(k) for k in range(self.tabs.count())]
        while name in existing:
            i += 1
            name = f"{base} ({i})"

        board = BoardWidget(name)
        if auto_load:
            board.load_data()

        idx = self.tabs.addTab(board, name)
        self.tabs.setCurrentIndex(idx)
        return board

    def rename_tab_dialog(self, index):
        if index < 0:
            return
        board = self.tabs.widget(index)
        new_name, ok = QInputDialog.getText(
            self, "Переименовать доску", "Новое название:", text=board.board_name
        )
        if ok and new_name.strip() and new_name.strip() != board.board_name:
            board.rename_to(new_name.strip())
            self.tabs.setTabText(index, new_name.strip())

    def tab_context_menu(self, pos):
        index = self.tabs.tabBar().tabAt(pos)
        if index < 0:
            return
        menu = QMenu(self)
        rename_action = menu.addAction("✏  Переименовать")
        close_action = menu.addAction("✕  Закрыть доску")
        menu.addSeparator()
        new_action = menu.addAction("＋  Новая доска")
        action = menu.exec(self.tabs.tabBar().mapToGlobal(pos))
        if action == rename_action:
            self.rename_tab_dialog(index)
        elif action == close_action:
            self.close_tab(index)
        elif action == new_action:
            self.create_new_board_dialog()

    def close_tab(self, index):
        board = self.tabs.widget(index)
        if self.tabs.count() == 1:
            reply = QMessageBox.question(
                self, "Закрыть последнюю доску",
                "Это последняя доска. Удалить её вместе с задачами?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        else:
            reply = QMessageBox.question(
                self, "Закрыть доску",
                f"Закрыть доску «{board.board_name}»?\n"
                "Файл с задачами сохранится, и её можно будет открыть снова при следующем запуске.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        board.save_data()
        self.tabs.removeTab(index)
        board.deleteLater()

    def closeEvent(self, event):
        for i in range(self.tabs.count()):
            board = self.tabs.widget(i)
            if hasattr(board, "save_data"):
                board.save_data()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = KanbanWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()