import sys
import os
import shutil
from zipfile import ZipFile
from functools import partial
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QComboBox, QStackedLayout, 
    QGroupBox, QProgressDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QPalette

# ---------- validación ----------
class Validador:
    @staticmethod
    def npn_ok(npn: str) -> bool:
        return npn.isdigit() and len(npn) == 30

# ---------- Hilo para compresión ZIP ----------
class ZipWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, root_dir, zip_path):
        super().__init__()
        self.root_dir = root_dir
        self.zip_path = zip_path

    def run(self):
        try:
            with ZipFile(self.zip_path, 'w') as zf:
                # Calcular total de archivos
                total_files = sum([len(files) for r, d, files in os.walk(self.root_dir)])
                processed = 0
                
                for root, dirs, files in os.walk(self.root_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, self.root_dir)
                        
                        # Omitir archivos ZIP existentes
                        if not file.lower().endswith('.zip'):
                            zf.write(file_path, rel_path)
                        
                        processed += 1
                        progress = int((processed / total_files) * 100) if total_files > 0 else 100
                        self.progress.emit(progress)
            
            self.finished.emit(self.zip_path)
        except Exception as e:
            self.error.emit(f"Error al crear ZIP: {str(e)}")

# ---------- clase base ----------
class BaseApp(QWidget):
    def __init__(self):
        super().__init__()
        self.root_dir = None
        self.current_npn = None
        self.facade_saved = False
        self.no_conv_fachada = None
        self.clasificaciones = {c: None for c in
            ["fachada", "estructura", "acabadosprincipales", "bano", "cocina"]}
        self.w_clas = {}
        self.anexos = []
        self.zip_worker = None

    # ---- helpers básicos ----
    def _campo_npn_unidad_ok(self) -> bool:
        npn = self.inp_npn.text().strip()
        unidad = self.inp_unidad.text().strip()
        if not Validador.npn_ok(npn):
            QMessageBox.warning(self, "NPN inválido",
                              "NPN debe tener exactamente 30 dígitos numéricos.")
            return False
        if not unidad:
            QMessageBox.warning(self, "Unidad requerida",
                              "El campo UNIDAD no puede estar vacío.")
            return False
        return True

    def _mayus(self):
        self.inp_unidad.setText(self.inp_unidad.text().upper())
        
    def _aplicar_estilo_boton(self, boton, color_name):
        pastel_colors = {
            "blue": "#A7C7E7",
            "green": "#B5EAD7",
            "pink": "#FFDAC1",
            "yellow": "#FFF6B7",
            "purple": "#D5AAFF",
            "gray": "#ECECEC",
        }
        color = pastel_colors.get(color_name.lower(), "#ECECEC")
        boton.setStyleSheet(f"""
    QPushButton {{
        background-color: {color};
        color: #333333;
        font-weight: bold;
        border: 1px solid #AAAAAA;
        padding: 5px;
        border-radius: 6px;
    }}
    QPushButton:hover {{
        background-color: #ffffff;
    }}
    """)


    def _build_campos(self, layout: QVBoxLayout):
        # NPN
        hb_npn = QHBoxLayout()
        hb_npn.addWidget(QLabel("NPN"))
        self.inp_npn = QLineEdit()
        hb_npn.addWidget(self.inp_npn)
        
        # Botón Guardar NPN
        self.btn_npn = QPushButton("Guardar NPN / Cambio de NPN")
        self.btn_npn.clicked.connect(self._guardar_npn)
        self._aplicar_estilo_boton(self.btn_npn, "blue")
        hb_npn.addWidget(self.btn_npn)
        
        layout.addLayout(hb_npn)
        self.inp_npn.textChanged.connect(
            lambda: self.inp_npn.setText(
                ''.join(filter(str.isdigit, self.inp_npn.text()))[:30]))

        # UNIDAD
        self.inp_unidad = QLineEdit()
        layout.addWidget(QLabel("UNIDAD"))
        layout.addWidget(self.inp_unidad)
        self.inp_unidad.textChanged.connect(self._mayus)

        # Tipo construcción
        self.cmb_tipo = QComboBox()
        self.cmb_tipo.addItems(["Convencional", "No Convencional"])
        layout.addWidget(QLabel("Tipo de Construcción"))
        layout.addWidget(self.cmb_tipo)

    # ---- función de renombrado ----
    def _renombrar_archivo(self, npn, unidad, tipo, src, clasificacion="", anexo_num=0):
        """Genera el nombre estructurado para el archivo"""
        ext = os.path.splitext(src)[1].lower()
        
        if tipo == "Convencional":
            if clasificacion == "fachada":
                return f"{npn}_fachada{ext}"
            else:
                return f"{npn}_{unidad}_{clasificacion}{ext}"
        else:
            if clasificacion == "fachada":
                return f"{npn}_fachada{ext}"
            else:
                return f"{npn}_{unidad}_anexo{anexo_num}{ext}"

# ---------- módulo MASIVO ----------
class MasivoApp(BaseApp):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Módulo Masivo")
        self._ui()

    def _ui(self):
        lay = QVBoxLayout(self)

        # botón de ayuda
        help_btn = QPushButton("📖 Instrucciones")
        help_btn.clicked.connect(self._help)
        lay.addWidget(help_btn)

        # campos básicos
        self._build_campos(lay)

        # grupo clasificaciones conv.
        self.grp = QGroupBox("Clasificaciones (Convencional)")
        g_lay = QVBoxLayout()
        for c in self.clasificaciones:
            hb = QHBoxLayout()
            btn = QPushButton(c)
            btn.clicked.connect(partial(self._sel_img, c))
            lbl = QLabel(); lbl.setFixedWidth(20)
            hb.addWidget(btn); hb.addWidget(lbl)
            g_lay.addLayout(hb)
            self.w_clas[c] = (btn, lbl)
        self.grp.setLayout(g_lay)
        lay.addWidget(self.grp)

        # fachada/no conv + anexos
        self.btn_fach_nc = QPushButton("Seleccionar fachada (No Convencional)")
        self.btn_fach_nc.clicked.connect(self._sel_fachada_nc)
        lay.addWidget(self.btn_fach_nc)

        self.btn_anexo = QPushButton("Agregar imagen ANEXO")
        self.btn_anexo.clicked.connect(self._sel_anexo)
        lay.addWidget(self.btn_anexo)

        # botones guardado
        self.btn_unit = QPushButton("Guardar Unidad / Cambio de Unidad")
        self.btn_unit.clicked.connect(self._guardar_unidad)
        self._aplicar_estilo_boton(self.btn_unit, "blue")
        lay.addWidget(self.btn_unit)

        # zip final - EN VERDE
        self.btn_zip = QPushButton("Generar ZIP Final")
        self.btn_zip.clicked.connect(self._zip_final)
        self._aplicar_estilo_boton(self.btn_zip, "green")
        lay.addWidget(self.btn_zip)

        self.setLayout(lay)
        self._toggle()
        self.cmb_tipo.currentIndexChanged.connect(self._toggle)

    # ---------- UI callbacks ----------
    def _help(self):
        QMessageBox.information(self, "Ayuda módulo masivo", """
1. Pulsa **Guardar NPN** para iniciar un nuevo predio.
2. Carga UNIDADES con **Guardar Unidad** tantas veces como necesites.
3. Al finalizar todos los NPN/Unidades, pulsa **Generar ZIP Final** para obtener
   un único archivo con todas las fotos.
""")

    def _toggle(self):
        conv = self.cmb_tipo.currentText() == "Convencional"
        self.grp.setVisible(conv)
        self.btn_fach_nc.setVisible(not conv)
        self.btn_anexo.setVisible(not conv)

    def _sel_img(self, clas):
        path, _ = QFileDialog.getOpenFileName(self, f"Escoger {clas}")
        if path:
            self.clasificaciones[clas] = path
            self.w_clas[clas][1].setText("✓")

    def _sel_fachada_nc(self):
        path, _ = QFileDialog.getOpenFileName(self, "Escoger fachada (No Convencional)")
        if path:
            self.no_conv_fachada = path
            self.btn_fach_nc.setText("Fachada NC ✓")

    def _sel_anexo(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Escoger ANEXOS")
        if paths:
            self.anexos.extend(paths)
            self.btn_anexo.setText(f"Anexos: {len(self.anexos)} ✓")

    # ---------- lógica NPN ----------
    def _guardar_npn(self):
        npn = self.inp_npn.text().strip()
        if not Validador.npn_ok(npn):
            QMessageBox.warning(self, "NPN inválido", "NPN debe ser 30 dígitos.")
            return

        if self.root_dir is None:
            dir_sel = QFileDialog.getExistingDirectory(
                self, "Selecciona carpeta raíz para los predios")
            if not dir_sel:
                return
            self.root_dir = dir_sel

        # Crear carpeta raíz si no existe
        os.makedirs(self.root_dir, exist_ok=True)

        self.current_npn = npn
        self.facade_saved = False
        self.no_conv_fachada = None
        self.clasificaciones = {c: None for c in self.clasificaciones}
        for _, lbl in self.w_clas.values():
            lbl.setText("")
        self.anexos.clear()
        self.btn_anexo.setText("Agregar imagen ANEXO")
        self.btn_fach_nc.setText("Seleccionar fachada (No Convencional)")
        self.inp_unidad.clear()
        QMessageBox.information(self, "NPN listo", f"Predio listo: {npn}")

    # ---------- lógica UNIDAD ----------
    def _guardar_unidad(self):
        if self.current_npn is None:
            QMessageBox.warning(self, "Primero NPN", "Guarda un NPN antes.")
            return
        if not self._campo_unidad_ok():
            return
        
        # Validación reforzada de imágenes
        tipo = self.cmb_tipo.currentText()
        if tipo == "Convencional":
            if not any(self.clasificaciones.values()):
                QMessageBox.warning(self, "Imágenes faltantes", 
                                   "¡ALERTA! Debes seleccionar al menos una imagen antes de guardar la unidad.")
                return
            if not self.clasificaciones["fachada"]:
                QMessageBox.warning(self, "Fachada faltante", 
                                   "¡ALERTA! La imagen de FACHADA es obligatoria.")
                return
        else:
            if not self.no_conv_fachada:
                QMessageBox.warning(self, "Fachada faltante", 
                                   "¡ALERTA! La imagen de FACHADA es obligatoria para No Convencional.")
                return
            if not self.anexos:
                QMessageBox.warning(self, "Anexos faltantes", 
                                   "¡ALERTA! Debes agregar al menos un ANEXO.")
                return

        npn = self.current_npn
        unidad = self.inp_unidad.text().strip()
        tipo = self.cmb_tipo.currentText()

        # Crear estructura de carpetas
        predio_dir = os.path.join(self.root_dir, npn)
        unidad_dir = os.path.join(predio_dir, unidad)
        os.makedirs(unidad_dir, exist_ok=True)

        # Copia adicional en raíz para el ZIP final
        copia_raiz_dir = os.path.join(self.root_dir, "TODAS_LAS_IMAGENES")
        os.makedirs(copia_raiz_dir, exist_ok=True)

        if tipo == "Convencional":
            # Fachada única
            if not self.facade_saved and self.clasificaciones["fachada"]:
                src = self.clasificaciones["fachada"]
                # RENOMBRAR ARCHIVO
                nuevo_nombre = self._renombrar_archivo(npn, "", tipo, src, "fachada")
                
                # Guardar en estructura de carpetas
                shutil.copyfile(src, os.path.join(predio_dir, nuevo_nombre))
                
                # Guardar copia adicional en raíz
                shutil.copyfile(src, os.path.join(copia_raiz_dir, nuevo_nombre))
                
                self.facade_saved = True
            
            # Otras clasificaciones
            for k, src in self.clasificaciones.items():
                if k == "fachada" or not src: 
                    continue
                # RENOMBRAR ARCHIVO
                nuevo_nombre = self._renombrar_archivo(npn, unidad, tipo, src, k)
                
                # Guardar en estructura de carpetas
                shutil.copyfile(src, os.path.join(unidad_dir, nuevo_nombre))
                
                # Guardar copia adicional en raíz
                shutil.copyfile(src, os.path.join(copia_raiz_dir, nuevo_nombre))
        else:  # No Convencional
            # Fachada
            if not self.facade_saved and self.no_conv_fachada:
                # RENOMBRAR ARCHIVO
                nuevo_nombre = self._renombrar_archivo(npn, "", tipo, self.no_conv_fachada, "fachada")
                
                # Guardar en estructura de carpetas
                shutil.copyfile(self.no_conv_fachada, os.path.join(predio_dir, nuevo_nombre))
                
                # Guardar copia adicional en raíz
                shutil.copyfile(self.no_conv_fachada, os.path.join(copia_raiz_dir, nuevo_nombre))
                
                self.facade_saved = True
            
            # Anexos
            for i, src in enumerate(self.anexos, 1):
                # RENOMBRAR ARCHIVO
                nuevo_nombre = self._renombrar_archivo(npn, unidad, tipo, src, "", i)
                
                # Guardar en estructura de carpetas
                shutil.copyfile(src, os.path.join(unidad_dir, nuevo_nombre))
                
                # Guardar copia adicional en raíz
                shutil.copyfile(src, os.path.join(copia_raiz_dir, nuevo_nombre))

        QMessageBox.information(self, "Unidad guardada",
                              f"Se guardó la unidad {unidad} en {npn}.")
        self._reset_unit_checks()

    def _campo_unidad_ok(self):
        unidad = self.inp_unidad.text().strip()
        if not unidad:
            QMessageBox.warning(self, "Unidad requerida", "Ingresa la UNIDAD.")
            return False
        return True

    def _reset_unit_checks(self):
        for c in self.clasificaciones:
            if c != "fachada" or self.facade_saved:
                self.clasificaciones[c] = None
                self.w_clas[c][1].clear()
        self.anexos.clear()
        self.btn_anexo.setText("Agregar imagen ANEXO")
        self.btn_fach_nc.setText("Seleccionar fachada (No Convencional)")
        self.inp_unidad.clear()

    # ---------- ZIP final ----------
    def _zip_final(self):
        if self.root_dir is None:
            QMessageBox.warning(self, "Sin datos", "No hay carpeta raíz definida.")
            return

        # Usar solo la carpeta TODAS_LAS_IMAGENES
        copia_raiz_dir = os.path.join(self.root_dir, "TODAS_LAS_IMAGENES")

        # Verificar existencia y contenido
        if not os.path.exists(copia_raiz_dir) or not any(
            os.path.isfile(os.path.join(copia_raiz_dir, f)) for f in os.listdir(copia_raiz_dir)
        ):
            QMessageBox.warning(self, "Sin datos", "No hay imágenes guardadas para generar el ZIP.")
            return

        # Preguntar dónde guardar el ZIP
        zip_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar archivo ZIP",
            os.path.join(self.root_dir, "masivo_fotos.zip"),
            "Archivos ZIP (*.zip)"
        )
        if not zip_path:
            return

        # Crear y configurar el hilo de compresión
        self.zip_worker = ZipWorker(copia_raiz_dir, zip_path)
        self.zip_worker.finished.connect(self._on_zip_finished)
        self.zip_worker.error.connect(self._on_zip_error)
        self.zip_worker.progress.connect(self._on_zip_progress)

        # Mostrar mensaje de progreso
        self.progress_dialog = QProgressDialog("Generando archivo ZIP...", "Cancelar", 0, 100, self)
        self.progress_dialog.setWindowTitle("Progreso")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.canceled.connect(self._cancel_zip)
        self.progress_dialog.show()

        self.zip_worker.start()


    def _on_zip_finished(self, zip_path):
        self.progress_dialog.close()
        QMessageBox.information(self, "ZIP Final",
                              f"ZIP creado exitosamente:\n{zip_path}")

    def _on_zip_error(self, error_msg):
        self.progress_dialog.close()
        QMessageBox.critical(self, "Error", error_msg)

    def _on_zip_progress(self, value):
        self.progress_dialog.setValue(value)

    def _cancel_zip(self):
        if self.zip_worker and self.zip_worker.isRunning():
            self.zip_worker.terminate()
        self.progress_dialog.close()

# ---------- módulo INDIVIDUAL ----------
class IndividualApp(MasivoApp):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Módulo Individual")
        self.btn_npn.setVisible(False)
        self.btn_unit.setVisible(False)
        self.btn_zip.setText("Generar ZIP")
        # Cambiar color del ZIP a VERDE
        self._aplicar_estilo_boton(self.btn_zip, "green")
        self.root_dir = None

    def _guardar_npn(self):
        pass

    def _guardar_unidad(self):
        pass

    def create_zip_structure(self, npn, unidad, tipo):
        # Crear carpeta para el NPN en la carpeta de origen
        npn_dir = os.path.join(self.root_dir, npn)
        os.makedirs(npn_dir, exist_ok=True)
        
        if tipo == "Convencional":
            for k, src in self.clasificaciones.items():
                if src:
                    # RENOMBRAR ARCHIVO
                    nuevo_nombre = self._renombrar_archivo(npn, unidad, tipo, src, k)
                    shutil.copyfile(src, os.path.join(npn_dir, nuevo_nombre))
        else:
            if self.no_conv_fachada:
                # RENOMBRAR ARCHIVO
                nuevo_nombre = self._renombrar_archivo(npn, unidad, tipo, self.no_conv_fachada, "fachada")
                shutil.copyfile(self.no_conv_fachada, os.path.join(npn_dir, nuevo_nombre))
            for i, src in enumerate(self.anexos, 1):
                # RENOMBRAR ARCHIVO
                nuevo_nombre = self._renombrar_archivo(npn, unidad, tipo, src, "", i)
                shutil.copyfile(src, os.path.join(npn_dir, nuevo_nombre))
        
        return npn_dir

    def create_zip(self):
        if not self._campo_npn_unidad_ok():
            return
        
        npn = self.inp_npn.text().strip()
        unidad = self.inp_unidad.text().strip()
        tipo = self.cmb_tipo.currentText()
        
        # Validación reforzada de imágenes
        if tipo == "Convencional":
            if not any(self.clasificaciones.values()):
                QMessageBox.warning(self, "Imágenes faltantes", 
                                   "¡ALERTA! Debes seleccionar al menos una imagen antes de generar el ZIP.")
                return
            if not self.clasificaciones["fachada"]:
                QMessageBox.warning(self, "Fachada faltante", 
                                   "¡ALERTA! La imagen de FACHADA es obligatoria.")
                return
        else:
            if not self.no_conv_fachada:
                QMessageBox.warning(self, "Fachada faltante", 
                                   "¡ALERTA! La imagen de FACHADA es obligatoria para No Convencional.")
                return
            if not self.anexos:
                QMessageBox.warning(self, "Anexos faltantes", 
                                   "¡ALERTA! Debes agregar al menos un ANEXO.")
                return
        
        # Usar carpeta de la primera imagen como raíz
        origen = self.clasificaciones["fachada"] or self.no_conv_fachada or (self.anexos[0] if self.anexos else None)
        if not origen:
            QMessageBox.warning(self, "Falta imagen", "Selecciona las imágenes antes.")
            return
        self.root_dir = os.path.dirname(origen)

        # Crear estructura en carpeta del NPN
        npn_dir = self.create_zip_structure(npn, unidad, tipo)
        zip_path = os.path.join(self.root_dir, f"{npn}.zip")
        
        # Crear ZIP con todo el contenido de la carpeta del NPN
        with ZipFile(zip_path, "w") as zf:
            for root, _, files in os.walk(npn_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, npn_dir)
                    zf.write(file_path, os.path.join(npn, rel_path))
        
        QMessageBox.information(self, "ZIP creado", f"ZIP generado:\n{zip_path}")
        self._reset_unit_checks()

    def _zip_final(self):
        self.create_zip()

# ---------- selector ----------
class Selector(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Selector de Módulo")
        self.setFixedSize(680, 640)
        lay = QVBoxLayout(self)

        self.combo = QComboBox()
        self.combo.addItems(["Elegir módulo...", "Módulo Masivo", "Módulo Individual"])
        lay.addWidget(QLabel("Selecciona módulo de trabajo"))
        lay.addWidget(self.combo)

        self.stack = QStackedLayout()
        self.stack.addWidget(QWidget())  # placeholder
        self.masivo = MasivoApp()
        self.individual = IndividualApp()
        self.stack.addWidget(self.masivo)
        self.stack.addWidget(self.individual)
        lay.addLayout(self.stack)

        self.combo.currentIndexChanged.connect(lambda i: self.stack.setCurrentIndex(i))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Selector()
    w.show()
    sys.exit(app.exec_())