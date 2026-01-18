import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog,
    QMessageBox, QStyleFactory, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont


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
        indent = '  ' * depth
        folder_name = os.path.basename(dirpath)
        structure.append(f"{indent}{folder_name}")
    return structure


class FolderStructureApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Structify - Folder Structure Replicator")
        self.resize(1440, 620)
        self.setMinimumSize(QSize(1200, 520))

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

        self.last_txt_dir = os.getcwd()

        # Left panel
        self._setup_panel(
            panels_layout,
            "Source Folder 1",
            "left",
            self.scan_left,
            self.export_left,
            self.import_txt_left,  # renamed method
            self.replicate_left,
            self.browse_left_source,
            self.browse_left_dest
        )

        # Right panel
        self._setup_panel(
            panels_layout,
            "Source Folder 2",
            "right",
            self.scan_right,
            self.export_right,
            self.import_txt_right,  # renamed method
            self.replicate_right,
            self.browse_right_source,
            self.browse_right_dest
        )

    def _setup_panel(self, parent_layout, title_text, prefix, scan_cb, export_cb, import_cb, replicate_cb,
                     browse_source_cb, browse_dest_cb):
        layout = QVBoxLayout()
        layout.setSpacing(12)
        parent_layout.addLayout(layout, stretch=1)

        title = QLabel(title_text)
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        # Source path
        path_layout = QHBoxLayout()
        path_layout.setSpacing(8)
        path_label = QLabel("Source:")
        path_label.setFixedWidth(70)
        path_layout.addWidget(path_label)
        edit = QLineEdit()
        edit.setPlaceholderText("Select a folder...")
        edit.setText(os.getcwd())
        path_layout.addWidget(edit)
        btn_browse = QPushButton("Browse")
        btn_browse.setFixedWidth(90)
        btn_browse.clicked.connect(browse_source_cb)
        path_layout.addWidget(btn_browse)
        layout.addLayout(path_layout)
        setattr(self, f"{prefix}_path_edit", edit)

        # Scan mode
        scan_mode_layout = QHBoxLayout()
        scan_mode_layout.setSpacing(16)

        radio_only_root = QRadioButton("Only direct subfolders (root level)")
        radio_recursive = QRadioButton("All subfolders (recursive scan)")
        radio_recursive.setChecked(True)

        group = QButtonGroup(self)
        group.addButton(radio_only_root)
        group.addButton(radio_recursive)

        scan_mode_layout.addWidget(radio_only_root)
        scan_mode_layout.addWidget(radio_recursive)
        scan_mode_layout.addStretch()
        layout.addLayout(scan_mode_layout)

        setattr(self, f"{prefix}_radio_only_root", radio_only_root)
        setattr(self, f"{prefix}_radio_recursive", radio_recursive)

        # Action buttons (Scan + Export + Import TXT)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_scan = QPushButton("Scan")
        btn_scan.clicked.connect(scan_cb)

        btn_export = QPushButton("Export TXT")
        btn_export.clicked.connect(export_cb)

        btn_import = QPushButton("Import TXT")
        btn_import.clicked.connect(import_cb)

        for btn in (btn_scan, btn_export, btn_import):
            btn.setFixedHeight(36)
            btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)

        setattr(self, f"{prefix}_btn_scan", btn_scan)
        setattr(self, f"{prefix}_btn_export", btn_export)
        setattr(self, f"{prefix}_btn_import", btn_import)

        # Preview
        preview_label = QLabel("Structure Preview")
        preview_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(preview_label)

        preview = QTextEdit()
        preview.setReadOnly(True)
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

        # Import TXT source folder (renamed label)
        txt_source_layout = QHBoxLayout()
        txt_source_layout.setSpacing(8)
        txt_label = QLabel("Import TXT from: (optional)")
        txt_label.setFixedWidth(170)
        txt_source_layout.addWidget(txt_label)
        txt_edit = QLineEdit()
        txt_edit.setPlaceholderText("Optional — preferred starting folder for .txt files")
        txt_source_layout.addWidget(txt_edit)
        btn_txt_browse = QPushButton("Browse")
        btn_txt_browse.setFixedWidth(90)
        btn_txt_browse.clicked.connect(lambda: self.browse_txt_source(prefix))
        txt_source_layout.addWidget(btn_txt_browse)
        layout.addLayout(txt_source_layout)
        setattr(self, f"{prefix}_txt_source_edit", txt_edit)

        # Destination
        dest_layout = QHBoxLayout()
        dest_layout.setSpacing(8)
        dest_label = QLabel("Destination:")
        dest_label.setFixedWidth(70)
        dest_layout.addWidget(dest_label)
        dest_edit = QLineEdit()
        dest_edit.setPlaceholderText("Select folder where you want to replicate the previewed structure")
        dest_layout.addWidget(dest_edit)
        btn_dest_browse = QPushButton("Browse")
        btn_dest_browse.setFixedWidth(90)
        btn_dest_browse.clicked.connect(browse_dest_cb)
        dest_layout.addWidget(btn_dest_browse)
        layout.addLayout(dest_layout)
        setattr(self, f"{prefix}_dest_edit", dest_edit)

        # Replicate button (bottom)
        replicate_layout = QHBoxLayout()
        replicate_layout.addStretch()
        btn_replicate = QPushButton("Replicate Preview")
        btn_replicate.clicked.connect(replicate_cb)
        btn_replicate.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: white;
                font-weight: bold;
                min-width: 180px;
            }
            QPushButton:hover { background-color: #0077e6; }
            QPushButton:pressed { background-color: #0055b3; }
        """)
        btn_replicate.setFixedHeight(40)
        replicate_layout.addWidget(btn_replicate)
        layout.addLayout(replicate_layout)

    # ── Helpers ────────────────────────────────────────
    def browse_txt_source(self, prefix):
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select preferred TXT folder (optional)",
            getattr(self, f"{prefix}_txt_source_edit").text() or self.last_txt_dir
        )
        if folder:
            getattr(self, f"{prefix}_txt_source_edit").setText(folder)
            self.last_txt_dir = folder

    def _load_txt_to_preview(self, prefix):
        edit = getattr(self, f"{prefix}_txt_source_edit")
        start_dir = edit.text().strip() or self.last_txt_dir

        txt_file, _ = QFileDialog.getOpenFileName(
            self,
            "Select folder structure .txt file",
            start_dir,
            "Text files (*.txt);;All files (*.*)"
        )
        if not txt_file:
            return False

        try:
            with open(txt_file, encoding="utf-8") as f:
                lines = [line.rstrip() for line in f if line.strip() and not line.strip().startswith('#')]

            preview = getattr(self, f"{prefix}_preview")
            preview.setPlainText("\n".join(lines))

            self.last_txt_dir = os.path.dirname(txt_file)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot load TXT file:\n{str(e)}")
            return False

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
        recursive = self.left_radio_recursive.isChecked()
        try:
            lines = get_folder_structure(path, recursive)
            self.left_preview.setPlainText("\n".join(lines))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot read structure:\n{str(e)}")

    def export_left(self):
        path = self.left_path_edit.text().strip()
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Error", "Invalid source folder.")
            return
        recursive = self.left_radio_recursive.isChecked()
        try:
            lines = get_folder_structure(path, recursive)
            txt_path = os.path.join(path, "folder_structure.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            QMessageBox.information(self, "Done", f"Saved to:\n{txt_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")

    def import_txt_left(self):
        self._load_txt_to_preview("left")

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
            QMessageBox.critical(self, "Error", f"Failed to replicate:\n{str(e)}")

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
        recursive = self.right_radio_recursive.isChecked()
        try:
            lines = get_folder_structure(path, recursive)
            self.right_preview.setPlainText("\n".join(lines))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot read structure:\n{str(e)}")

    def export_right(self):
        path = self.right_path_edit.text().strip()
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Error", "Invalid source folder.")
            return
        recursive = self.right_radio_recursive.isChecked()
        try:
            lines = get_folder_structure(path, recursive)
            txt_path = os.path.join(path, "folder_structure.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            QMessageBox.information(self, "Done", f"Saved to:\n{txt_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")

    def import_txt_right(self):
        self._load_txt_to_preview("right")

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
            QMessageBox.critical(self, "Error", f"Failed to replicate:\n{str(e)}")

    # ── Core creation logic ────────────────────────────
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


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = FolderStructureApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()