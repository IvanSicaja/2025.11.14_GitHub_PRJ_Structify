import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog,
    QMessageBox, QStyleFactory
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon

def get_folder_structure(root_path):
    """Returns only folder tree with 2-space indentation"""
    structure = []
    for dirpath, dirnames, _ in os.walk(root_path, topdown=True):
        dirnames.sort()  # consistent order
        rel_path = os.path.relpath(dirpath, root_path)
        if rel_path == '.':
            continue
        depth = rel_path.count(os.sep)
        indent = '  ' * depth
        folder_name = os.path.basename(dirpath)
        structure.append(f"{indent}{folder_name}")
    return structure

class FolderStructureApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Folder Structure")
        self.resize(720, 580)
        self.setMinimumSize(QSize(600, 480))

        # Try to use a modern style
        if 'Fusion' in QStyleFactory.keys():
            QApplication.setStyle('Fusion')

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(12)

        # ── Path row ───────────────────────────────────────
        path_layout = QHBoxLayout()
        path_layout.setSpacing(8)

        self.path_label = QLabel("Folder:")
        self.path_label.setFixedWidth(70)
        path_layout.addWidget(self.path_label)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Select a folder...")
        self.path_edit.setText(os.getcwd())
        path_layout.addWidget(self.path_edit)

        self.btn_browse = QPushButton("Browse")
        self.btn_browse.setFixedWidth(90)
        self.btn_browse.clicked.connect(self.browse_folder)
        path_layout.addWidget(self.btn_browse)

        self.main_layout.addLayout(path_layout)

        # ── Action buttons ─────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_scan = QPushButton("Scan")
        self.btn_scan.clicked.connect(self.scan_structure)

        self.btn_export = QPushButton("Export TXT")
        self.btn_export.clicked.connect(self.export_txt)

        self.btn_create = QPushButton("Create from TXT")
        self.btn_create.clicked.connect(self.create_from_txt)

        for btn in (self.btn_scan, self.btn_export, self.btn_create):
            btn.setFixedHeight(36)
            btn_layout.addWidget(btn)

        self.main_layout.addLayout(btn_layout)

        # ── Preview area ───────────────────────────────────
        preview_label = QLabel("Structure Preview")
        preview_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.main_layout.addWidget(preview_label)

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("SF Mono", 12))  # or Menlo, Monaco, Consolas
        self.preview.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #d0d4d8;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        self.main_layout.addWidget(self.preview, stretch=1)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", self.path_edit.text())
        if folder:
            self.path_edit.setText(folder)

    def scan_structure(self):
        path = self.path_edit.text().strip()
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Error", "Selected path is not a valid folder.")
            return

        try:
            lines = get_folder_structure(path)
            self.preview.setPlainText("\n".join(lines))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot read structure:\n{str(e)}")

    def export_txt(self):
        path = self.path_edit.text().strip()
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Error", "Invalid folder.")
            return

        try:
            lines = get_folder_structure(path)
            txt_path = os.path.join(path, "folder_structure.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            QMessageBox.information(self, "Done", f"Saved to:\n{txt_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")

    def create_from_txt(self):
        path = self.path_edit.text().strip()
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Error", "Please select a valid destination folder.")
            return

        txt_file, _ = QFileDialog.getOpenFileName(
            self, "Select structure.txt", "", "Text files (*.txt);;All files (*.*)"
        )
        if not txt_file:
            return

        try:
            with open(txt_file, encoding="utf-8") as f:
                lines = [line.rstrip() for line in f if line.strip()]

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

            QMessageBox.information(self, "Success", "Folder structure created.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create folders:\n{str(e)}")

def main():
    app = QApplication(sys.argv)
    # Optional: try to get more macOS-like appearance
    app.setStyle("Fusion")
    # You can also set app.setStyleSheet(...) with more custom CSS

    window = FolderStructureApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()