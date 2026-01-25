import sys
import os
import subprocess
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog,
    QMessageBox, QStyleFactory, QRadioButton, QButtonGroup,
    QDialog, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor

LAST_PATHS_FILE = "structify_last_paths.json"


def get_folder_structure(root_path, recursive=True):
    structure = []
    if not recursive:
        for name in sorted(os.listdir(root_path)):
            full_path = os.path.join(root_path, name)
            if os.path.isdir(full_path):
                structure.append(name)
        return structure

    for dirpath, dirnames, _ in os.walk(root_path, topdown=True):
        dirnames.sort()
        rel_path = os.path.relpath(dirpath, root_path)
        if rel_path == '.':
            continue
        depth = rel_path.count(os.sep)
        indent = '  ' * depth
        folder_name = os.path.basename(dirpath)
        structure.append(f"{indent}{folder_name}")
    return structure


class ComparisonDialog(QDialog):
    def __init__(self, left_lines, right_lines, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Structure Comparison")
        self.resize(1000, 700)

        layout = QVBoxLayout(self)
        label = QLabel("Comparison: Left vs Right preview (order-insensitive per level)")
        label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(label)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("SF Mono", 12))
        self.preview.setStyleSheet("""
            QTextEdit {
                background-color: #fafafa;
                color: #000000;
                border: 1px solid #c0c0c0;
                border-radius: 6px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.preview, stretch=1)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btn_box.accepted.connect(self.accept)
        layout.addWidget(btn_box)

        self._compare_and_highlight(left_lines, right_lines)

    def _compare_and_highlight(self, left_lines, right_lines):
        doc = self.preview.document()
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()

        green = QColor("#e6ffe6")
        red = QColor("#ffe6e6")
        gray = QColor("#f0f0f0")

        left_by_level = {}
        right_by_level = {}

        for line in left_lines:
            indent = len(line) - len(line.lstrip())
            level = indent // 2
            name = line.strip()
            if level not in left_by_level:
                left_by_level[level] = set()
            if name:
                left_by_level[level].add(name)

        for line in right_lines:
            indent = len(line) - len(line.lstrip())
            level = indent // 2
            name = line.strip()
            if level not in right_by_level:
                right_by_level[level] = set()
            if name:
                right_by_level[level].add(name)

        max_level = max(
            max(left_by_level.keys(), default=0),
            max(right_by_level.keys(), default=0)
        )

        for level in range(max_level + 1):
            left_names = left_by_level.get(level, set())
            right_names = right_by_level.get(level, set())

            common = sorted(left_names & right_names)
            for name in common:
                fmt = QTextCharFormat()
                fmt.setBackground(green)
                cursor.setCharFormat(fmt)
                cursor.insertText(f"  {'  ' * level}{name}\n")

            only_left = sorted(left_names - right_names)
            for name in only_left:
                fmt = QTextCharFormat()
                fmt.setBackground(red)
                cursor.setCharFormat(fmt)
                cursor.insertText(f"L {'  ' * level}{name}\n")

            only_right = sorted(right_names - left_names)
            for name in only_right:
                fmt = QTextCharFormat()
                fmt.setBackground(red)
                cursor.setCharFormat(fmt)
                cursor.insertText(f"R {'  ' * level}{name}\n")

            if level < max_level:
                cursor.insertText("\n")

        cursor.endEditBlock()
        self.preview.setTextCursor(cursor)


class FolderStructureApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Structify - Folder Structure Replicator")
        self.resize(1440, 680)
        self.setMinimumSize(QSize(1200, 580))

        if 'Fusion' in QStyleFactory.keys():
            QApplication.setStyle('Fusion')

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(12)

        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(16)
        self.main_layout.addLayout(panels_layout, stretch=1)

        # Left panel
        self._setup_panel(panels_layout, "Source Folder 1", "left",
                          self.scan_left, self.export_left, self.import_txt_left,
                          self.browse_left_source)

        # Right panel
        self._setup_panel(panels_layout, "Source Folder 2", "right",
                          self.scan_right, self.export_right, self.import_txt_right,
                          self.browse_right_source)

        # Bottom controls: only the three main action buttons in one row
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(40)
        bottom_layout.setContentsMargins(0, 20, 0, 20)
        bottom_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addLayout(bottom_layout)

        btn_rep_left = QPushButton("Replicate Left Preview")
        btn_rep_left.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: white;
                font-weight: bold;
                min-width: 220px;
            }
            QPushButton:hover { background-color: #0077e6; }
            QPushButton:pressed { background-color: #0055b3; }
        """)
        btn_rep_left.setFixedHeight(48)
        btn_rep_left.clicked.connect(self.replicate_left)
        bottom_layout.addWidget(btn_rep_left)

        btn_compare = QPushButton("Compare Structures")
        btn_compare.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                min-width: 220px;
            }
            QPushButton:hover { background-color: #66BB6A; }
            QPushButton:pressed { background-color: #388E3C; }
        """)
        btn_compare.setFixedHeight(48)
        btn_compare.clicked.connect(self.compare_previews)
        bottom_layout.addWidget(btn_compare)

        btn_rep_right = QPushButton("Replicate Right Preview")
        btn_rep_right.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: white;
                font-weight: bold;
                min-width: 220px;
            }
            QPushButton:hover { background-color: #0077e6; }
            QPushButton:pressed { background-color: #0055b3; }
        """)
        btn_rep_right.setFixedHeight(48)
        btn_rep_right.clicked.connect(self.replicate_right)
        bottom_layout.addWidget(btn_rep_right)

        # Load last used source paths
        self._load_last_paths()

    def _setup_panel(self, parent_layout, title_text, prefix, scan_cb, export_cb, import_cb, browse_source_cb):
        layout = QVBoxLayout()
        layout.setSpacing(12)
        parent_layout.addLayout(layout, stretch=1)

        title = QLabel(title_text)
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        path_layout = QHBoxLayout()
        path_layout.setSpacing(8)
        path_label = QLabel("Source:")
        path_label.setFixedWidth(70)
        path_layout.addWidget(path_label)
        edit = QLineEdit()
        edit.setPlaceholderText("Select a folder...")
        path_layout.addWidget(edit)
        btn_browse = QPushButton("Browse")
        btn_browse.setFixedWidth(90)
        btn_browse.clicked.connect(browse_source_cb)
        path_layout.addWidget(btn_browse)
        layout.addLayout(path_layout)
        setattr(self, f"{prefix}_path_edit", edit)

        scan_mode_layout = QVBoxLayout()
        scan_mode_layout.setSpacing(6)
        radio_only_root = QRadioButton("Only direct subfolders (root level)")
        radio_recursive = QRadioButton("All subfolders (recursive scan)")
        radio_recursive.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(radio_only_root)
        group.addButton(radio_recursive)
        scan_mode_layout.addWidget(radio_only_root)
        scan_mode_layout.addWidget(radio_recursive)
        layout.addLayout(scan_mode_layout)
        setattr(self, f"{prefix}_radio_only_root", radio_only_root)
        setattr(self, f"{prefix}_radio_recursive", radio_recursive)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_scan = QPushButton("Scan")
        btn_export = QPushButton("Export Previewed TXT")
        btn_import = QPushButton("Import TXT")
        btn_scan.clicked.connect(scan_cb)
        btn_export.clicked.connect(export_cb)
        btn_import.clicked.connect(import_cb)
        for btn in (btn_scan, btn_export, btn_import):
            btn.setFixedHeight(36)
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)
        setattr(self, f"{prefix}_btn_scan", btn_scan)
        setattr(self, f"{prefix}_btn_export", btn_export)
        setattr(self, f"{prefix}_btn_import", btn_import)

        preview_label = QLabel("Structure Preview (editable)")
        preview_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(preview_label)

        preview = QTextEdit()
        preview.setReadOnly(False)
        preview.setFont(QFont("SF Mono", 12))
        preview.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #d0d4d8;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        layout.addWidget(preview, stretch=1)
        setattr(self, f"{prefix}_preview", preview)

    def _load_last_paths(self):
        try:
            if os.path.exists(LAST_PATHS_FILE):
                with open(LAST_PATHS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "left" in data and os.path.isdir(data["left"]):
                    self.left_path_edit.setText(data["left"])
                if "right" in data and os.path.isdir(data["right"]):
                    self.right_path_edit.setText(data["right"])
        except:
            pass

    def closeEvent(self, event):
        paths = {
            "left": self.left_path_edit.text().strip(),
            "right": self.right_path_edit.text().strip()
        }
        try:
            with open(LAST_PATHS_FILE, "w", encoding="utf-8") as f:
                json.dump(paths, f, indent=2)
        except:
            pass
        super().closeEvent(event)

    def compare_previews(self):
        left_text = self.left_preview.toPlainText()
        right_text = self.right_preview.toPlainText()
        left_lines = [line.rstrip() for line in left_text.splitlines()]
        right_lines = [line.rstrip() for line in right_text.splitlines()]
        if not left_lines and not right_lines:
            QMessageBox.information(self, "Compare", "Both previews are empty.")
            return
        dialog = ComparisonDialog(left_lines, right_lines, self)
        dialog.exec()

    # ── Export with overwrite protection ────────────────────────────────
    def _safe_export(self, source_path, content):
        if not content.strip():
            QMessageBox.warning(self, "Nothing to export", "The preview is empty.")
            return

        base_name = "folder_structure.txt"
        txt_path = os.path.join(source_path, base_name)

        # If file doesn't exist → save directly
        if not os.path.exists(txt_path):
            try:
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(content + "\n")
                self._show_export_success(txt_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")
            return

        # File exists → ask user
        msg = QMessageBox(self)
        msg.setWindowTitle("File Already Exists")
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setText(f"The file already exists:\n{txt_path}")
        msg.setInformativeText("What would you like to do?")

        overwrite_btn = msg.addButton("Overwrite", QMessageBox.ButtonRole.YesRole)
        newfile_btn = msg.addButton("Create numbered copy", QMessageBox.ButtonRole.NoRole)
        cancel_btn = msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

        msg.exec()

        clicked = msg.clickedButton()

        if clicked == overwrite_btn:
            try:
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(content + "\n")
                self._show_export_success(txt_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Overwrite failed:\n{str(e)}")

        elif clicked == newfile_btn:
            # Find next available number
            i = 1
            while True:
                new_name = f"folder_structure ({i}).txt"
                new_path = os.path.join(source_path, new_name)
                if not os.path.exists(new_path):
                    try:
                        with open(new_path, "w", encoding="utf-8") as f:
                            f.write(content + "\n")
                        self._show_export_success(new_path)
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Save failed:\n{str(e)}")
                    break
                i += 1

        # else: cancel → do nothing

    def _show_export_success(self, txt_path):
        msg = QMessageBox(self)
        msg.setWindowTitle("Export Successful")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText("Current preview exported")
        msg.setInformativeText(f"Location:\n{txt_path}")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        open_btn = msg.addButton("Open Folder", QMessageBox.ButtonRole.ActionRole)
        msg.exec()

        if msg.clickedButton() == open_btn:
            self._open_folder(os.path.dirname(txt_path))

    # Left export
    def export_left(self):
        path = self.left_path_edit.text().strip()
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Error", "Invalid source folder.")
            return

        content = self.left_preview.toPlainText().rstrip()
        self._safe_export(path, content)

    # Right export
    def export_right(self):
        path = self.right_path_edit.text().strip()
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Error", "Invalid source folder.")
            return

        content = self.right_preview.toPlainText().rstrip()
        self._safe_export(path, content)

    # ── Other methods unchanged ─────────────────────────────────────────
    def browse_left_source(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder", self.left_path_edit.text())
        if folder:
            self.left_path_edit.setText(folder)

    def scan_left(self):
        path = self.left_path_edit.text().strip()
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Error", "Selected source path is not a valid folder.")
            return
        recursive = self.left_radio_recursive.isChecked()
        try:
            lines = get_folder_structure(path, recursive)
            self.left_preview.setPlainText("\n".join(lines))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot read structure:\n{str(e)}")

    def import_txt_left(self):
        txt_file, _ = QFileDialog.getOpenFileName(
            self, "Select structure .txt file", "",
            "Text files (*.txt);;All files (*.*)"
        )
        if not txt_file:
            return
        try:
            with open(txt_file, encoding="utf-8") as f:
                lines = [line.rstrip() for line in f if line.strip() and not line.strip().startswith('#')]
            self.left_preview.setPlainText("\n".join(lines))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot load TXT file:\n{str(e)}")

    def replicate_left(self):
        preview_text = self.left_preview.toPlainText()
        lines = [line.rstrip() for line in preview_text.splitlines() if line.strip()]
        if not lines:
            QMessageBox.warning(self, "Error", "No structure in preview to replicate.")
            return
        dest_folder = QFileDialog.getExistingDirectory(
            self, "Select folder where you want to create the structure"
        )
        if not dest_folder:
            return
        if not os.path.isdir(dest_folder):
            QMessageBox.warning(self, "Error", "Selected path is not a valid folder.")
            return
        try:
            self.create_from_lines(dest_folder, lines)
            msg = QMessageBox(self)
            msg.setWindowTitle("Replication Successful")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText("Folder structure replicated.")
            msg.setInformativeText(f"Created in:\n{dest_folder}")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            open_btn = msg.addButton("Open Folder", QMessageBox.ButtonRole.ActionRole)
            msg.exec()
            if msg.clickedButton() == open_btn:
                self._open_folder(dest_folder)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to replicate:\n{str(e)}")

    def browse_right_source(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder", self.right_path_edit.text())
        if folder:
            self.right_path_edit.setText(folder)

    def scan_right(self):
        path = self.right_path_edit.text().strip()
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Error", "Selected source path is not a valid folder.")
            return
        recursive = self.right_radio_recursive.isChecked()
        try:
            lines = get_folder_structure(path, recursive)
            self.right_preview.setPlainText("\n".join(lines))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot read structure:\n{str(e)}")

    def import_txt_right(self):
        txt_file, _ = QFileDialog.getOpenFileName(
            self, "Select structure .txt file", "",
            "Text files (*.txt);;All files (*.*)"
        )
        if not txt_file:
            return
        try:
            with open(txt_file, encoding="utf-8") as f:
                lines = [line.rstrip() for line in f if line.strip() and not line.strip().startswith('#')]
            self.right_preview.setPlainText("\n".join(lines))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot load TXT file:\n{str(e)}")

    def replicate_right(self):
        preview_text = self.right_preview.toPlainText()
        lines = [line.rstrip() for line in preview_text.splitlines() if line.strip()]
        if not lines:
            QMessageBox.warning(self, "Error", "No structure in preview to replicate.")
            return
        dest_folder = QFileDialog.getExistingDirectory(
            self, "Select folder where you want to create the structure"
        )
        if not dest_folder:
            return
        if not os.path.isdir(dest_folder):
            QMessageBox.warning(self, "Error", "Selected path is not a valid folder.")
            return
        try:
            self.create_from_lines(dest_folder, lines)
            msg = QMessageBox(self)
            msg.setWindowTitle("Replication Successful")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText("Folder structure replicated.")
            msg.setInformativeText(f"Created in:\n{dest_folder}")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            open_btn = msg.addButton("Open Folder", QMessageBox.ButtonRole.ActionRole)
            msg.exec()
            if msg.clickedButton() == open_btn:
                self._open_folder(dest_folder)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to replicate:\n{str(e)}")

    def _open_folder(self, path):
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def create_from_lines(self, path, lines):
        stack = [path]
        for line in lines:
            indent = len(line) - len(line.lstrip())
            level = indent // 2
            name = line.strip()
            while len(stack) > level + 1:
                stack.pop()
            current = os.path.join(stack[-1], name)
            os.makedirs(current, exist_ok=True)
            stack.append(current)

    def _load_last_paths(self):
        try:
            if os.path.exists(LAST_PATHS_FILE):
                with open(LAST_PATHS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "left" in data and os.path.isdir(data["left"]):
                    self.left_path_edit.setText(data["left"])
                if "right" in data and os.path.isdir(data["right"]):
                    self.right_path_edit.setText(data["right"])
        except:
            pass

    def closeEvent(self, event):
        paths = {
            "left": self.left_path_edit.text().strip(),
            "right": self.right_path_edit.text().strip()
        }
        try:
            with open(LAST_PATHS_FILE, "w", encoding="utf-8") as f:
                json.dump(paths, f, indent=2)
        except:
            pass
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = FolderStructureApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()