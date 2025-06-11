import sys
import os
import shutil
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QComboBox, QTextEdit, QGroupBox
)
from PyQt5.QtGui import QIcon
from zipfile import ZipFile

class ImagenRenombrador(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Herramienta de Categorización Fotográfica")
        self.setGeometry(100, 100, 500, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Botón de instrucciones
        instrucciones_btn = QPushButton()
        instrucciones_btn.setIcon(QIcon.fromTheme("dialog-information"))
        instrucciones_btn.setText(" Instrucciones")
        instrucciones_btn.clicked.connect(self.mostrar_instrucciones)
        layout.addWidget(instrucciones_btn)

        # NPN
        self.npn_input = QLineEdit()
        layout.addWidget(QLabel("NPN"))
        layout.addWidget(self.npn_input)

        # UNIDAD
        self.unidad_input = QLineEdit()
        layout.addWidget(QLabel("UNIDAD"))
        layout.addWidget(self.unidad_input)

        # Tipo de módulo
        self.modulo_combo = QComboBox()
        self.modulo_combo.addItems(["modulo predio individual", "modulo masivo (M2, M3, M5)"])
        self.modulo_combo.currentIndexChanged.connect(self.actualizar_modo)
        layout.addWidget(QLabel("Tipo de módulo"))
        layout.addWidget(self.modulo_combo)

        # Total de unidades (solo en masivo)
        self.total_unidades_input = QLineEdit()
        self.total_unidades_input.setPlaceholderText("Ej: 5")
        layout.addWidget(QLabel("Total de Unidades (solo para masivo)"))
        layout.addWidget(self.total_unidades_input)
        self.total_unidades_input.hide()

        # Tipo de construcción
        self.tipo_construccion = QComboBox()
        self.tipo_construccion.addItems(["Convencional", "No Convencional"])
        self.tipo_construccion.currentIndexChanged.connect(self.actualizar_clasificaciones)
        layout.addWidget(QLabel("Tipo de Construcción"))
        layout.addWidget(self.tipo_construccion)

        # Clasificaciones (solo si convencional)
        self.clasificaciones = {
            "fachada": None,
            "estructura": None,
            "acabadosprincipales": None,
            "bano": None,
            "cocina": None
        }
        self.botones_clasificaciones = QGroupBox("Clasificaciones")
        clasif_layout = QVBoxLayout()
        for clas in self.clasificaciones:
            btn = QPushButton(f"Seleccionar imagen: {clas}")
            btn.clicked.connect(lambda _, c=clas: self.seleccionar_imagen(c))
            clasif_layout.addWidget(btn)
        self.botones_clasificaciones.setLayout(clasif_layout)
        layout.addWidget(self.botones_clasificaciones)

        # Clasificación Anexo (solo si no convencional)
        self.anexo_imagenes = []
        self.anexo_btn = QPushButton("Agregar imagen ANEXO")
        self.anexo_btn.clicked.connect(self.seleccionar_anexo)
        layout.addWidget(self.anexo_btn)
        self.anexo_btn.hide()

        # Botón generar ZIP
        generar_btn = QPushButton("Generar ZIP")
        generar_btn.clicked.connect(self.generar_zip)
        layout.addWidget(generar_btn)

        self.setLayout(layout)
        self.actualizar_clasificaciones()

    def mostrar_instrucciones(self):
        QMessageBox.information(self, "Instrucciones", """
1. Ingresa el NPN y la UNIDAD.
2. Selecciona el módulo: individual o masivo (M2, M3, M5).
3. Define si es Convencional o No Convencional.
4. Si es Convencional, carga las imágenes por clasificación.
5. Si es No Convencional, solo sube imágenes tipo ANEXO.
6. En modo masivo, indica el total de unidades.
7. Haz clic en 'Generar ZIP'. El archivo se guarda donde estaban las imágenes.
        """)

    def actualizar_modo(self):
        es_masivo = "masivo" in self.modulo_combo.currentText().lower()
        self.total_unidades_input.setVisible(es_masivo)

    def actualizar_clasificaciones(self):
        if self.tipo_construccion.currentText() == "Convencional":
            self.botones_clasificaciones.show()
            self.anexo_btn.hide()
        else:
            self.botones_clasificaciones.hide()
            self.anexo_btn.show()

    def seleccionar_imagen(self, clasificacion):
        ruta, _ = QFileDialog.getOpenFileName(self, f"Seleccionar imagen para {clasificacion}")
        if ruta:
            self.clasificaciones[clasificacion] = ruta

    def seleccionar_anexo(self):
        rutas, _ = QFileDialog.getOpenFileNames(self, "Seleccionar imagen(es) ANEXO")
        if rutas:
            self.anexo_imagenes.extend(rutas)

    def generar_zip(self):
        npn = self.npn_input.text().strip()
        unidad = self.unidad_input.text().strip()
        modulo = self.modulo_combo.currentText()
        tipo = self.tipo_construccion.currentText()
        total_unidades = self.total_unidades_input.text().strip()

        if not npn or not unidad:
            QMessageBox.warning(self, "Campos requeridos", "Debes ingresar NPN y UNIDAD.")
            return

        if "masivo" in modulo and not total_unidades.isdigit():
            QMessageBox.warning(self, "Total unidades", "Debes ingresar un número válido de unidades.")
            return

        origen = None
        estructura_final = {}

        if tipo == "Convencional":
            for clas, ruta in self.clasificaciones.items():
                if not ruta:
                    QMessageBox.warning(self, "Falta imagen", f"Falta imagen para {clas}.")
                    return
                if not origen:
                    origen = os.path.dirname(ruta)
                estructura_final[f"{npn}_{unidad}_{clas}{os.path.splitext(ruta)[1]}"] = ruta
        else:
            if not self.anexo_imagenes:
                QMessageBox.warning(self, "Falta imagen", "Debes agregar al menos una imagen tipo ANEXO.")
                return
            origen = os.path.dirname(self.anexo_imagenes[0])
            for i, ruta in enumerate(self.anexo_imagenes, 1):
                nombre = f"{npn}_{unidad}_anexo{os.path.splitext(ruta)[1]}"
                estructura_final[nombre] = ruta

        # Estructura de carpetas
        if "masivo" in modulo:
            carpeta_base = os.path.join(origen, f"{npn}_masivo")
            carpeta_img = os.path.join(carpeta_base, "imagenes")
            os.makedirs(carpeta_img, exist_ok=True)

            for nombre, ruta in estructura_final.items():
                shutil.copyfile(ruta, os.path.join(carpeta_img, nombre))

            with open(os.path.join(carpeta_base, f"{npn}.txt"), "w") as f:
                f.write(f"NPN: {npn}\nTotal de unidades: {total_unidades}")
        else:
            carpeta_base = os.path.join(origen, npn, unidad)
            os.makedirs(carpeta_base, exist_ok=True)
            for nombre, ruta in estructura_final.items():
                shutil.copyfile(ruta, os.path.join(carpeta_base, nombre))

        # Generar ZIP
        zip_path = os.path.join(origen, f"{npn}.zip")
        with ZipFile(zip_path, 'w') as zipf:
            for root, _, files in os.walk(os.path.join(origen, npn) if "masivo" not in modulo else carpeta_base):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, os.path.dirname(carpeta_base))
                    zipf.write(abs_path, rel_path)

        QMessageBox.information(self, "Éxito", f"ZIP generado correctamente en:\n{zip_path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ventana = ImagenRenombrador()
    ventana.show()
    sys.exit(app.exec_())
 