"""
Interfaz PyQt5 para registrar NPN y UNIDAD, seleccionar imágenes por categoría y renombrarlas
como <npn>_<unidad>_<categoria>.<ext>.
Todas las imágenes se copian a una carpeta <npn>_<unidad> creada en el mismo directorio
que la primera imagen seleccionada. Luego se genera automáticamente un archivo ZIP
<npn>_<unidad>.zip en esa misma ruta al pulsar "Empaquetar ZIP".
"""

import sys
import os
import shutil
from functools import partial
from typing import Dict, Tuple, Optional

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QMessageBox,
    QVBoxLayout,
    QFormLayout,
    QHBoxLayout,
    QGroupBox,
)

CATEGORIES = [
    "fachada",
    "estructura",
    "acabados_principales",
    "baños",
    "cocina",
]

class ImageRenamer(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Renombrar imágenes por categoría")
        self.base_dir: Optional[str] = None  # Directorio de la primera imagen
        self.dest_dir: Optional[str] = None  # Carpeta <npn>_<unidad>
        self._setup_ui()

    def _setup_ui(self) -> None:
        central = QWidget()
        main_layout = QVBoxLayout()

        form_layout = QFormLayout()
        self.npn_edit = QLineEdit()
        self.unidad_edit = QLineEdit()
        form_layout.addRow("NPN:", self.npn_edit)
        form_layout.addRow("UNIDAD:", self.unidad_edit)
        main_layout.addLayout(form_layout)

        group_box = QGroupBox("Selecciona las imágenes por categoría")
        group_layout = QVBoxLayout()
        self.file_paths: Dict[str, str] = {}
        for cat in CATEGORIES:
            h_layout = QHBoxLayout()
            label = QLabel("No seleccionada")
            btn = QPushButton(f"Elegir {cat}")
            btn.clicked.connect(partial(self._select_file, cat, label))
            h_layout.addWidget(btn)
            h_layout.addWidget(label)
            group_layout.addLayout(h_layout)
        group_box.setLayout(group_layout)
        main_layout.addWidget(group_box)

        zip_btn = QPushButton("Empaquetar ZIP")
        zip_btn.clicked.connect(self._zip_images)
        main_layout.addWidget(zip_btn)

        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.close)
        main_layout.addWidget(close_btn)

        central.setLayout(main_layout)
        self.setCentralWidget(central)

    # ────────────────────────────────────────────────────────────────────────
    # Selección de archivos
    # ────────────────────────────────────────────────────────────────────────
    def _select_file(self, category: str, label: QLabel) -> None:
        npn, unidad = self._collect_ids()
        if not (npn and unidad):
            QMessageBox.warning(self, "Campos requeridos", "Debes completar NPN y UNIDAD antes de continuar.")
            return
        src, _ = QFileDialog.getOpenFileName(
            self,
            f"Selecciona imagen de {category}",
            "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp)"
        )
        if not src:
            return
        try:
            new_path = self._copy_and_rename(src, npn, unidad, category)
            self.file_paths[category] = new_path
            label.setText(os.path.basename(new_path))
        except Exception as exc:  # pylint: disable=broad-except
            QMessageBox.critical(self, "Error", str(exc))

    def _collect_ids(self) -> Tuple[str, str]:
        return self.npn_edit.text().strip(), self.unidad_edit.text().strip()

    # ────────────────────────────────────────────────────────────────────────
    # Copia y renombrado
    # ────────────────────────────────────────────────────────────────────────
    def _copy_and_rename(self, src_path: str, npn: str, unidad: str, category: str) -> str:
        if self.base_dir is None:
            self.base_dir = os.path.dirname(src_path)
            self.dest_dir = os.path.join(self.base_dir, f"{npn}_{unidad}")
            os.makedirs(self.dest_dir, exist_ok=True)
        if self.dest_dir is None:
            raise RuntimeError("No se ha definido el directorio de destino.")
        _, ext = os.path.splitext(src_path)
        dest_path = os.path.join(self.dest_dir, f"{npn}_{unidad}_{category}{ext.lower()}")
        shutil.copy2(src_path, dest_path)
        return dest_path

    # ────────────────────────────────────────────────────────────────────────
    # Empaquetado ZIP
    # ────────────────────────────────────────────────────────────────────────
    def _zip_images(self) -> None:
        if not self.dest_dir or not os.path.isdir(self.dest_dir):
            QMessageBox.warning(self, "Sin archivos", "Aún no has seleccionado imágenes válidas.")
            return
        zip_name = f"{self.dest_dir}.zip"
        try:
            if os.path.exists(zip_name):
                os.remove(zip_name)
            shutil.make_archive(self.dest_dir, "zip", self.dest_dir)
            QMessageBox.information(self, "ZIP creado", f"Se creó {zip_name}")
        except Exception as exc:  # pylint: disable=broad-except
            QMessageBox.critical(self, "Error al comprimir", str(exc))


def main() -> None:
    app = QApplication(sys.argv)
    window = ImageRenamer()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
