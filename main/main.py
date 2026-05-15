import sys
import os
import subprocess
import json
from datetime import date
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog,
    QMessageBox, QStyleFactory, QRadioButton, QButtonGroup,
    QDialog, QDialogButtonBox, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor

LAST_PATHS_FILE = "structify_last_paths.json"


def get_folder_structure(root_path, recursive=True, include_folders=True, include_files=True):
    structure = []

    if not recursive:
        try:
            entries = sorted(os.listdir(root_path))
        except PermissionError:
            return structure
        for name in entries:
            full_path = os.path.join(root_path, name)
            if os.path.isdir(full_path) and include_folders:
                structure.append(name)
            elif os.path.isfile(full_path) and include_files:
                structure.append(name)
        return structure

    for dirpath, dirnames, filenames in os.walk(root_path, topdown=True):
        dirnames.sort()
        rel_path = os.path.relpath(dirpath, root_path)
        if rel_path == '.':
            depth = 0
        else:
            depth = rel_path.count(os.sep) + 1

        indent = '  ' * (depth - 1) if depth > 0 else ''

        if rel_path != '.':
            folder_name = os.path.basename(dirpath)
            if include_folders:
                structure.append(f"{indent}{folder_name}")
            child_indent = '  ' * depth
        else:
            child_indent = ''

        if include_files:
            for fname in sorted(filenames):
                structure.append(f"{child_indent}{fname}")

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
        self.resize(1440, 780)
        self.setMinimumSize(QSize(1200, 680))

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

        # ── Bottom controls ──────────────────────────────────────────────────
        bottom_layout = QVBoxLayout()
        bottom_layout.setSpacing(8)
        bottom_layout.setContentsMargins(0, 12, 0, 0)
        self.main_layout.addLayout(bottom_layout)

        # Row 1: Replicate + Compare + Replicate
        row1 = QHBoxLayout()
        row1.setSpacing(40)
        row1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_layout.addLayout(row1)

        btn_rep_left = QPushButton("Replicate Left Preview")
        btn_rep_left.setStyleSheet(self._blue_btn_style())
        btn_rep_left.setFixedHeight(48)
        btn_rep_left.clicked.connect(self.replicate_left)
        row1.addWidget(btn_rep_left)

        btn_compare = QPushButton("Compare Structures")
        btn_compare.setStyleSheet(self._green_btn_style())
        btn_compare.setFixedHeight(48)
        btn_compare.clicked.connect(self.compare_previews)
        row1.addWidget(btn_compare)

        btn_rep_right = QPushButton("Replicate Right Preview")
        btn_rep_right.setStyleSheet(self._blue_btn_style())
        btn_rep_right.setFixedHeight(48)
        btn_rep_right.clicked.connect(self.replicate_right)
        row1.addWidget(btn_rep_right)

        # ── Divider ──
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #d0d0d0;")
        bottom_layout.addWidget(divider)

        # Row 2: Batch Rename section
        rename_label = QLabel("Batch Rename  —  Left preview = current names  |  Right preview = new names  (line-by-line, same order)")
        rename_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #333;")
        rename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_layout.addWidget(rename_label)

        # Explanation label (replaces the search path row)
        info_label = QLabel("The search will automatically use the Left source folder as the search location.")
        info_label.setStyleSheet("font-size: 13px; color: white;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_layout.addWidget(info_label)

        row2 = QHBoxLayout()
        row2.setSpacing(20)
        row2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_layout.addLayout(row2)

        btn_rename = QPushButton("⟳  Rename Items (Left → Right)")
        btn_rename.setStyleSheet("""
            QPushButton {
                background-color: #e65c00;
                color: white;
                font-weight: bold;
                font-size: 13px;
                min-width: 260px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #ff6a00; }
            QPushButton:pressed { background-color: #c24f00; }
        """)
        btn_rename.setFixedHeight(42)
        btn_rename.clicked.connect(self.batch_rename)
        row2.addWidget(btn_rename)

        # Copyright
        copyright_layout = QHBoxLayout()
        copyright_layout.setContentsMargins(0, 8, 0, 4)
        copyright_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addLayout(copyright_layout)
        copyright_label = QLabel("Developed by Ivan Sicaja © 2026. All rights reserved.")
        copyright_label.setStyleSheet("color: #666666; font-size: 12px; font-style: italic;")
        copyright_layout.addWidget(copyright_label)

        self._load_last_paths()

    # ── Style helpers ────────────────────────────────────────────────────────
    def _blue_btn_style(self):
        return """
            QPushButton {
                background-color: #0066cc; color: white;
                font-weight: bold; min-width: 220px; border-radius: 6px;
            }
            QPushButton:hover { background-color: #0077e6; }
            QPushButton:pressed { background-color: #0055b3; }
        """

    def _green_btn_style(self):
        return """
            QPushButton {
                background-color: #4CAF50; color: white;
                font-weight: bold; min-width: 220px; border-radius: 6px;
            }
            QPushButton:hover { background-color: #66BB6A; }
            QPushButton:pressed { background-color: #388E3C; }
        """

    # ── Panel setup ──────────────────────────────────────────────────────────
    def _setup_panel(self, parent_layout, title_text, prefix, scan_cb, export_cb, import_cb, browse_source_cb):
        layout = QVBoxLayout()
        layout.setSpacing(10)
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
        path_layout.addWidget(edit)
        btn_browse = QPushButton("Browse")
        btn_browse.setFixedWidth(90)
        btn_browse.clicked.connect(browse_source_cb)
        path_layout.addWidget(btn_browse)
        layout.addLayout(path_layout)
        setattr(self, f"{prefix}_path_edit", edit)

        # ── Scan depth options ──
        depth_layout = QHBoxLayout()
        depth_layout.setSpacing(16)
        radio_only_root = QRadioButton("Only direct children")
        radio_recursive = QRadioButton("All subfolders (recursive)")
        radio_recursive.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(radio_only_root)
        group.addButton(radio_recursive)
        depth_layout.addWidget(radio_only_root)
        depth_layout.addWidget(radio_recursive)
        depth_layout.addStretch()
        layout.addLayout(depth_layout)
        setattr(self, f"{prefix}_radio_only_root", radio_only_root)
        setattr(self, f"{prefix}_radio_recursive", radio_recursive)

        # ── Scan content options ──
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)
        content_label = QLabel("Scan:")
        content_label.setStyleSheet("font-size: 12px; color: #444;")
        content_layout.addWidget(content_label)

        cb_folders = QCheckBox("Folder names")
        cb_folders.setChecked(True)
        cb_files = QCheckBox("File names")
        cb_files.setChecked(False)

        # Keep at least one checked
        def make_guard(this_cb, other_cb):
            def guard(state):
                if not this_cb.isChecked() and not other_cb.isChecked():
                    this_cb.setChecked(True)
            return guard

        cb_folders.stateChanged.connect(make_guard(cb_folders, cb_files))
        cb_files.stateChanged.connect(make_guard(cb_files, cb_folders))

        content_layout.addWidget(cb_folders)
        content_layout.addWidget(cb_files)
        content_layout.addStretch()
        layout.addLayout(content_layout)
        setattr(self, f"{prefix}_cb_folders", cb_folders)
        setattr(self, f"{prefix}_cb_files", cb_files)

        # ── Action buttons ──
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

    # ── Persistence ──────────────────────────────────────────────────────────
    def _load_last_paths(self):
        try:
            if os.path.exists(LAST_PATHS_FILE):
                with open(LAST_PATHS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "left" in data and os.path.isdir(data["left"]):
                    self.left_path_edit.setText(data["left"])
                if "right" in data and os.path.isdir(data["right"]):
                    self.right_path_edit.setText(data["right"])
        except Exception:
            pass

    def closeEvent(self, event):
        paths = {
            "left": self.left_path_edit.text().strip(),
            "right": self.right_path_edit.text().strip()
        }
        try:
            with open(LAST_PATHS_FILE, "w", encoding="utf-8") as f:
                json.dump(paths, f, indent=2)
        except Exception:
            pass
        super().closeEvent(event)

    # ── Scan ─────────────────────────────────────────────────────────────────
    def _do_scan(self, prefix):
        path_edit = getattr(self, f"{prefix}_path_edit")
        path = path_edit.text().strip()
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Error", "Selected source path is not a valid folder.")
            return
        recursive = getattr(self, f"{prefix}_radio_recursive").isChecked()
        include_folders = getattr(self, f"{prefix}_cb_folders").isChecked()
        include_files = getattr(self, f"{prefix}_cb_files").isChecked()
        try:
            lines = get_folder_structure(path, recursive, include_folders, include_files)
            getattr(self, f"{prefix}_preview").setPlainText("\n".join(lines))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot read structure:\n{str(e)}")

    def scan_left(self):
        self._do_scan("left")

    def scan_right(self):
        self._do_scan("right")

    # ── Browse ───────────────────────────────────────────────────────────────
    def browse_left_source(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder", self.left_path_edit.text())
        if folder:
            self.left_path_edit.setText(folder)

    def browse_right_source(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder", self.right_path_edit.text())
        if folder:
            self.right_path_edit.setText(folder)

    # ── Import / Export ──────────────────────────────────────────────────────
    def _safe_export(self, source_path, content):
        if not content.strip():
            QMessageBox.warning(self, "Nothing to export", "The preview is empty.")
            return

        today = date.today().strftime("%Y.%m.%d")
        folder_name = os.path.basename(source_path)
        safe_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in folder_name).strip("_")
        base_name = f"{today}_folder-structure_{safe_name}.txt"
        txt_path = os.path.join(source_path, base_name)

        if not os.path.exists(txt_path):
            try:
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(content + "\n")
                self._show_export_success(txt_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")
            return

        msg = QMessageBox(self)
        msg.setWindowTitle("File Already Exists")
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setText(f"The file already exists:\n{txt_path}")
        msg.setInformativeText("What would you like to do?")
        overwrite_btn = msg.addButton("Overwrite", QMessageBox.ButtonRole.YesRole)
        newfile_btn = msg.addButton("Create numbered copy", QMessageBox.ButtonRole.NoRole)
        msg.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
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
            i = 1
            while True:
                new_path = os.path.join(source_path, f"{today}_folder-structure_{safe_name}_{i:02d}.txt")
                if not os.path.exists(new_path):
                    try:
                        with open(new_path, "w", encoding="utf-8") as f:
                            f.write(content + "\n")
                        self._show_export_success(new_path)
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Save failed:\n{str(e)}")
                    break
                i += 1

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

    def export_left(self):
        path = self.left_path_edit.text().strip()
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Error", "Invalid source folder.")
            return
        self._safe_export(path, self.left_preview.toPlainText().rstrip())

    def export_right(self):
        path = self.right_path_edit.text().strip()
        if not os.path.isdir(path):
            QMessageBox.warning(self, "Error", "Invalid source folder.")
            return
        self._safe_export(path, self.right_preview.toPlainText().rstrip())

    def _import_txt(self, prefix):
        txt_file, _ = QFileDialog.getOpenFileName(
            self, "Select structure .txt file", "",
            "Text files (*.txt);;All files (*.*)"
        )
        if not txt_file:
            return
        try:
            with open(txt_file, encoding="utf-8") as f:
                lines = [line.rstrip() for line in f if line.strip() and not line.strip().startswith('#')]
            getattr(self, f"{prefix}_preview").setPlainText("\n".join(lines))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot load TXT file:\n{str(e)}")

    def import_txt_left(self):
        self._import_txt("left")

    def import_txt_right(self):
        self._import_txt("right")

    # ── Compare ──────────────────────────────────────────────────────────────
    def compare_previews(self):
        left_lines = [l.rstrip() for l in self.left_preview.toPlainText().splitlines()]
        right_lines = [l.rstrip() for l in self.right_preview.toPlainText().splitlines()]
        if not left_lines and not right_lines:
            QMessageBox.information(self, "Compare", "Both previews are empty.")
            return
        ComparisonDialog(left_lines, right_lines, self).exec()

    # ── Replicate ────────────────────────────────────────────────────────────
    def _replicate(self, prefix):
        preview = getattr(self, f"{prefix}_preview")
        lines = [l.rstrip() for l in preview.toPlainText().splitlines() if l.strip()]
        if not lines:
            QMessageBox.warning(self, "Error", "No structure in preview to replicate.")
            return
        dest_folder = QFileDialog.getExistingDirectory(
            self, "Select folder where you want to create the structure"
        )
        if not dest_folder or not os.path.isdir(dest_folder):
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

    def replicate_left(self):
        self._replicate("left")

    def replicate_right(self):
        self._replicate("right")

    # ── Batch Rename ─────────────────────────────────────────────────────────
    def batch_rename(self):
        """
        For each line pair (left_name, right_name):
          - Strip indentation to get just the bare name
          - Recursively search `search_root` for an entry with that name
          - Rename it to right_name (keeping it in its current parent folder)
          - Warn if anything is open / locked
        """
        left_lines_raw = self.left_preview.toPlainText().splitlines()
        right_lines_raw = self.right_preview.toPlainText().splitlines()

        left_lines = [l.rstrip() for l in left_lines_raw if l.strip()]
        right_lines = [l.rstrip() for l in right_lines_raw if l.strip()]

        if not left_lines or not right_lines:
            QMessageBox.warning(self, "Batch Rename", "Both previews must contain names.")
            return

        if len(left_lines) != len(right_lines):
            QMessageBox.warning(
                self, "Batch Rename",
                f"Line count mismatch!\nLeft: {len(left_lines)} lines  |  Right: {len(right_lines)} lines\n"
                "Both previews must have the same number of non-empty lines."
            )
            return

        # Determine search root (always use left source folder)
        search_root = self.left_path_edit.text().strip()
        if not os.path.isdir(search_root):
            QMessageBox.warning(self, "Batch Rename",
                                 "Please set a valid Left source folder path.")
            return

        # Build rename pairs (only where name actually changes)
        pairs = []
        for left_line, right_line in zip(left_lines, right_lines):
            old_name = left_line.strip()
            new_name = right_line.strip()
            if old_name and new_name and old_name != new_name:
                pairs.append((old_name, new_name))

        if not pairs:
            QMessageBox.information(self, "Batch Rename", "No differences found — nothing to rename.")
            return

        # Confirm
        preview_text = "\n".join(f"  {o}  →  {n}" for o, n in pairs[:20])
        if len(pairs) > 20:
            preview_text += f"\n  … and {len(pairs) - 20} more"

        confirm = QMessageBox(self)
        confirm.setWindowTitle("Confirm Batch Rename")
        confirm.setIcon(QMessageBox.Icon.Question)
        confirm.setText(f"About to rename {len(pairs)} item(s) inside:\n{search_root}")
        confirm.setInformativeText(
            f"Rename pairs:\n{preview_text}\n\n"
            "⚠  Make sure no files/folders are open in other programs before proceeding."
        )
        confirm.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
        if confirm.exec() != QMessageBox.StandardButton.Ok:
            return

        # Execute renames
        renamed = []
        failed = []

        for old_name, new_name in pairs:
            found = False
            for dirpath, dirnames, filenames in os.walk(search_root):
                # Check folders
                if old_name in dirnames:
                    old_full = os.path.join(dirpath, old_name)
                    new_full = os.path.join(dirpath, new_name)
                    try:
                        os.rename(old_full, new_full)
                        renamed.append(f"{old_full}  →  {new_name}")
                        found = True
                        # Update dirnames in-place so os.walk follows the renamed folder
                        idx = dirnames.index(old_name)
                        dirnames[idx] = new_name
                    except Exception as e:
                        failed.append(f"{old_full}: {e}")
                        found = True
                    break
                # Check files
                if old_name in filenames:
                    old_full = os.path.join(dirpath, old_name)
                    new_full = os.path.join(dirpath, new_name)
                    try:
                        os.rename(old_full, new_full)
                        renamed.append(f"{old_full}  →  {new_name}")
                        found = True
                    except Exception as e:
                        failed.append(f"{old_full}: {e}")
                        found = True
                    break
            if not found:
                failed.append(f'"{old_name}" — not found in {search_root}')

        # Result summary
        summary_parts = []
        if renamed:
            summary_parts.append(f"✅  Renamed {len(renamed)} item(s) successfully.")
        if failed:
            detail = "\n".join(failed[:20])
            if len(failed) > 20:
                detail += f"\n… and {len(failed) - 20} more"
            summary_parts.append(f"❌  {len(failed)} error(s):\n{detail}")

        msg = QMessageBox(self)
        msg.setWindowTitle("Batch Rename Complete")
        msg.setIcon(QMessageBox.Icon.Information if not failed else QMessageBox.Icon.Warning)
        msg.setText("\n\n".join(summary_parts))
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        open_btn = msg.addButton("Open Folder", QMessageBox.ButtonRole.ActionRole)
        msg.exec()
        if msg.clickedButton() == open_btn:
            self._open_folder(search_root)

    # ── Helpers ──────────────────────────────────────────────────────────────
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


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = FolderStructureApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()