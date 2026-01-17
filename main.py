import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog,
    QMessageBox, QStyleFactory, QCheckBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor


def get_folder_structure(root_path, recursive=True):
    """Return folder structure. If recursive=False, only root-level folders are listed."""
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
        indent = '  ' * depth  # consistent 2-space indent
        folder_name = os.path.basename(dirpath)
        structure.append(f"{indent}{folder_name}")
    return structure


class FolderStructureApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Structify - Folder Structure Replicator")
        self.resize(1440, 580)
        self.setMinimumSize(QSize(1200, 480))

        if 'Fusion' in QStyleFactory.keys():
            QApplication.setStyle('Fusion')

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(16, 16, 16, 16)
        self.main_layout.setSpacing(12)

        # Panels container
        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(16)
        self.main_layout.addLayout(panels_layout, stretch=1)

        # ── Left Panel ─────────────────────────────────────
        left_layout = QVBoxLayout()
        left_layout.setSpacing(12)
        panels_layout.addLayout(left_layout, stretch=1)

        left_title = QLabel("Source Folder 1")
        left_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_layout.addWidget(left_title)

        # Source path row
        left_path_layout = QHBoxLayout()
        left_path_layout.setSpacing(8)
        left_path_label = QLabel("Source:")
        left_path_label.setFixedWidth(70)
        left_path_layout.addWidget(left_path_label)
        self.left_path_edit = QLineEdit()
        self.left_path_edit.setPlaceholderText("Select a folder...")
        self.left_path_edit.setText(os.getcwd())
        left_path_layout.addWidget(self.left_path_edit)
        self.left_btn_browse = QPushButton("Browse")
        self.left_btn_browse.setFixedWidth(90)
        self.left_btn_browse.clicked.connect(self.browse_left_source)
        left_path_layout.addWidget(self.left_btn_browse)
        left_layout.addLayout(left_path_layout)

        # Options row
        left_options_layout = QHBoxLayout()
        left_options_layout.setSpacing(10)
        self.left_chk_recursive = QCheckBox("Scan subfolders recursively")
        self.left_chk_recursive.setChecked(True)
        left_options_layout.addWidget(self.left_chk_recursive)
        left_options_layout.addStretch()
        left_layout.addLayout(left_options_layout)

        # Action buttons
        left_btn_layout = QHBoxLayout()
        left_btn_layout.setSpacing(10)

        self.left_btn_scan = QPushButton("Scan")
        self.left_btn_scan.clicked.connect(self.scan_left)

        self.left_btn_export = QPushButton("Export TXT")
        self.left_btn_export.clicked.connect(self.export_left)

        self.left_btn_import = QPushButton("Import TXT")
        self.left_btn_import.clicked.connect(self.create_from_txt_left)

        self.left_btn_replicate = QPushButton("Replicate Preview")
        self.left_btn_replicate.clicked.connect(self.replicate_left)
        self.left_btn_replicate.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0077e6;
            }
            QPushButton:pressed {
                background-color: #0055b3;
            }
        """)

        for btn in (self.left_btn_scan, self.left_btn_export, self.left_btn_import, self.left_btn_replicate):
            btn.setFixedHeight(36)
            left_btn_layout.addWidget(btn)

        left_layout.addLayout(left_btn_layout)

        # Preview area
        left_preview_label = QLabel("Structure Preview")
        left_preview_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        left_layout.addWidget(left_preview_label)

        self.left_preview = QTextEdit()
        self.left_preview.setReadOnly(True)
        self.left_preview.setFont(QFont("SF Mono", 12))
        self.left_preview.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #d0d4d8;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        left_layout.addWidget(self.left_preview, stretch=1)

        # Destination path row
        left_dest_layout = QHBoxLayout()
        left_dest_layout.setSpacing(8)
        left_dest_label = QLabel("Destination:")
        left_dest_label.setFixedWidth(70)
        left_dest_layout.addWidget(left_dest_label)
        self.left_dest_edit = QLineEdit()
        self.left_dest_edit.setPlaceholderText("Select a folder to create structure in...")
        left_dest_layout.addWidget(self.left_dest_edit)
        self.left_btn_browse_dest = QPushButton("Browse")
        self.left_btn_browse_dest.setFixedWidth(90)
        self.left_btn_browse_dest.clicked.connect(self.browse_left_dest)
        left_dest_layout.addWidget(self.left_btn_browse_dest)
        left_layout.addLayout(left_dest_layout)

        # ── Right Panel ────────────────────────────────────
        right_layout = QVBoxLayout()
        right_layout.setSpacing(12)
        panels_layout.addLayout(right_layout, stretch=1)

        right_title = QLabel("Source Folder 2")
        right_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        right_layout.addWidget(right_title)

        # Source path row
        right_path_layout = QHBoxLayout()
        right_path_layout.setSpacing(8)
        right_path_label = QLabel("Source:")
        right_path_label.setFixedWidth(70)
        right_path_layout.addWidget(right_path_label)
        self.right_path_edit = QLineEdit()
        self.right_path_edit.setPlaceholderText("Select a folder...")
        self.right_path_edit.setText(os.getcwd())
        right_path_layout.addWidget(self.right_path_edit)
        self.right_btn_browse = QPushButton("Browse")
        self.right_btn_browse.setFixedWidth(90)
        self.right_btn_browse.clicked.connect(self.browse_right_source)
        right_path_layout.addWidget(self.right_btn_browse)
        right_layout.addLayout(right_path_layout)

        # Options row
        right_options_layout = QHBoxLayout()
        right_options_layout.setSpacing(10)
        self.right_chk_recursive = QCheckBox("Scan subfolders recursively")
        self.right_chk_recursive.setChecked(True)
        right_options_layout.addWidget(self.right_chk_recursive)
        right_options_layout.addStretch()
        right_layout.addLayout(right_options_layout)

        # Action buttons
        right_btn_layout = QHBoxLayout()
        right_btn_layout.setSpacing(10)

        self.right_btn_scan = QPushButton("Scan")
        self.right_btn_scan.clicked.connect(self.scan_right)

        self.right_btn_export = QPushButton("Export TXT")
        self.right_btn_export.clicked.connect(self.export_right)

        self.right_btn_import = QPushButton("Import TXT")
        self.right_btn_import.clicked.connect(self.create_from_txt_right)

        self.right_btn_replicate = QPushButton("Replicate Preview")
        self.right_btn_replicate.clicked.connect(self.replicate_right)
        self.right_btn_replicate.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0077e6;
            }
            QPushButton:pressed {
                background-color: #0055b3;
            }
        """)

        for btn in (self.right_btn_scan, self.right_btn_export, self.right_btn_import, self.right_btn_replicate):
            btn.setFixedHeight(36)
            right_btn_layout.addWidget(btn)

        right_layout.addLayout(right_btn_layout)

        # Preview area
        right_preview_label = QLabel("Structure Preview")
        right_preview_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        right_layout.addWidget(right_preview_label)

        self.right_preview = QTextEdit()
        self.right_preview.setReadOnly(True)
        self.right_preview.setFont(QFont("SF Mono", 12))
        self.right_preview.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #d0d4d8;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        right_layout.addWidget(self.right_preview, stretch=1)

        # Destination path row
        right_dest_layout = QHBoxLayout()
        right_dest_layout.setSpacing(8)
        right_dest_label = QLabel("Destination:")
        right_dest_label.setFixedWidth(70)
        right_dest_layout.addWidget(right_dest_label)
        self.right_dest_edit = QLineEdit()
        self.right_dest_edit.setPlaceholderText("Select a folder to create structure in...")
        right_dest_layout.addWidget(self.right_dest_edit)
        self.right_btn_browse_dest = QPushButton("Browse")
        self.right_btn_browse_dest.setFixedWidth(90)
        self.right_btn_browse_dest.clicked.connect(self.browse_right_dest)
        right_dest_layout.addWidget(self.right_btn_browse_dest)
        right_layout.addLayout(right_dest_layout)

    # ── Helper Methods ─────────────────────────────────
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

    # ── Left Panel Methods ─────────────────────────────
    def browse_left_source(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder", self.left_path_edit.text())
        if folder:
            self.left_path_edit.setText(folder)

    def browse_left_dest(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder", self.left_dest_edit.text())
        if folder:
            self.left_dest_edit.setText(folder)

    def scan_left(self):
        path = self.left_path_edit.text().strip()
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Error", "Selected source path is not a valid folder.")
            return
        try:
            lines = get_folder_structure(path, self.left_chk_recursive.isChecked())
            self.left_preview.setPlainText("\n".join(lines))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot read structure:\n{str(e)}")

    def export_left(self):
        path = self.left_path_edit.text().strip()
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Error", "Invalid source folder.")
            return
        try:
            lines = get_folder_structure(path, self.left_chk_recursive.isChecked())
            txt_path = os.path.join(path, "folder_structure.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            QMessageBox.information(self, "Done", f"Saved to:\n{txt_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")

    def create_from_txt_left(self):
        dest = self.left_dest_edit.text().strip()
        if not dest or not os.path.isdir(dest):
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
            self.create_from_lines(dest, lines)
            QMessageBox.information(self, "Success", "Folder structure created from TXT.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create folders:\n{str(e)}")

    def replicate_left(self):
        dest = self.left_dest_edit.text().strip()
        if not dest or not os.path.isdir(dest):
            QMessageBox.warning(self, "Error", "Please select a valid destination folder.")
            return
        preview_text = self.left_preview.toPlainText()
        lines = [line.rstrip() for line in preview_text.splitlines() if line.strip()]
        if not lines:
            QMessageBox.warning(self, "Error", "No structure in preview to replicate.")
            return
        try:
            self.create_from_lines(dest, lines)
            QMessageBox.information(self, "Success", "Folder structure replicated from preview.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to replicate structure:\n{str(e)}")

    # ── Right Panel Methods ────────────────────────────
    def browse_right_source(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder", self.right_path_edit.text())
        if folder:
            self.right_path_edit.setText(folder)

    def browse_right_dest(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder", self.right_dest_edit.text())
        if folder:
            self.right_dest_edit.setText(folder)

    def scan_right(self):
        path = self.right_path_edit.text().strip()
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Error", "Selected source path is not a valid folder.")
            return
        try:
            lines = get_folder_structure(path, self.right_chk_recursive.isChecked())
            self.right_preview.setPlainText("\n".join(lines))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot read structure:\n{str(e)}")

    def export_right(self):
        path = self.right_path_edit.text().strip()
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Error", "Invalid source folder.")
            return
        try:
            lines = get_folder_structure(path, self.right_chk_recursive.isChecked())
            txt_path = os.path.join(path, "folder_structure.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            QMessageBox.information(self, "Done", f"Saved to:\n{txt_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")

    def create_from_txt_right(self):
        dest = self.right_dest_edit.text().strip()
        if not dest or not os.path.isdir(dest):
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
            self.create_from_lines(dest, lines)
            QMessageBox.information(self, "Success", "Folder structure created from TXT.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create folders:\n{str(e)}")

    def replicate_right(self):
        dest = self.right_dest_edit.text().strip()
        if not dest or not os.path.isdir(dest):
            QMessageBox.warning(self, "Error", "Please select a valid destination folder.")
            return
        preview_text = self.right_preview.toPlainText()
        lines = [line.rstrip() for line in preview_text.splitlines() if line.strip()]
        if not lines:
            QMessageBox.warning(self, "Error", "No structure in preview to replicate.")
            return
        try:
            self.create_from_lines(dest, lines)
            QMessageBox.information(self, "Success", "Folder structure replicated from preview.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to replicate structure:\n{str(e)}")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = FolderStructureApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()