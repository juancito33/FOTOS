import sys, os, shutil
from zipfile import ZipFile
from functools import partial
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QComboBox, QStackedLayout, QGroupBox
)
from PyQt5.QtCore import Qt

# ---------- validación ----------
class Validador:
    @staticmethod
    def npn_ok(npn: str) -> bool:
        return npn.isdigit() and len(npn) == 30

# ---------- clase base ----------
class BaseApp(QWidget):
    def __init__(self):
        super().__init__()
        self.root_dir = None          # carpeta raíz para todas las salidas
        self.current_npn = None
        self.facade_saved = False
        self.no_conv_fachada = None
        self.clasificaciones = {c: None for c in
            ["fachada", "estructura", "acabadosprincipales", "bano", "cocina"]}
        self.w_clas = {}
        self.anexos = []

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

    def _build_campos(self, layout: QVBoxLayout):
        # NPN
        self.inp_npn = QLineEdit()
        layout.addWidget(QLabel("NPN"))
        layout.addWidget(self.inp_npn)
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
        self.btn_npn = QPushButton("Guardar NPN / Cambio de NPN")
        self.btn_npn.clicked.connect(self._guardar_npn)
        lay.addWidget(self.btn_npn)

        self.btn_unit = QPushButton("Guardar Unidad / Cambio de Unidad")
        self.btn_unit.clicked.connect(self._guardar_unidad)
        lay.addWidget(self.btn_unit)

        # zip final
        self.btn_zip = QPushButton("Generar ZIP Final")
        self.btn_zip.clicked.connect(self._zip_final)
        lay.addWidget(self.btn_zip)

        self.setLayout(lay)
        self._toggle()  # oculta elementos segun tipo

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

        # seleccionar raíz si es la primera vez
        if self.root_dir is None:
            dir_sel = QFileDialog.getExistingDirectory(
                self, "Selecciona carpeta raíz para los predios")
            if not dir_sel:
                return
            self.root_dir = dir_sel

        # crear carpeta npn
        npn_dir = os.path.join(self.root_dir, npn)
        os.makedirs(npn_dir, exist_ok=True)

        # reset estados internos
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
        QMessageBox.information(self, "NPN listo", f"Carpeta creada: {npn}")

    # ---------- lógica UNIDAD ----------
    def _guardar_unidad(self):
        if self.current_npn is None:
            QMessageBox.warning(self, "Primero NPN", "Guarda un NPN antes.")
            return
        if not self._campo_unidad_ok():
            return

        npn = self.current_npn
        unidad = self.inp_unidad.text().strip()
        tipo = self.cmb_tipo.currentText()

        predio_dir = os.path.join(self.root_dir, npn)
        unidad_dir = os.path.join(predio_dir, unidad)
        os.makedirs(unidad_dir, exist_ok=True)

        if tipo == "Convencional":
            # fachada única
            if not self.facade_saved and self.clasificaciones["fachada"]:
                src = self.clasificaciones["fachada"]
                shutil.copyfile(src,
                    os.path.join(predio_dir, f"{npn}_fachada{os.path.splitext(src)[1]}"))
                self.facade_saved = True
            # otras
            for k, src in self.clasificaciones.items():
                if k == "fachada": continue
                if src:
                    nombre = f"{npn}_{unidad}_{k}{os.path.splitext(src)[1]}"
                    shutil.copyfile(src, os.path.join(unidad_dir, nombre))
        else:  # No Convencional
            if not self.facade_saved and self.no_conv_fachada:
                ext = os.path.splitext(self.no_conv_fachada)[1]
                shutil.copyfile(self.no_conv_fachada,
                    os.path.join(predio_dir, f"{npn}_fachada{ext}"))
                self.facade_saved = True
            for i, src in enumerate(self.anexos, 1):
                nombre = f"{npn}_{unidad}_anexo{i}{os.path.splitext(src)[1]}"
                shutil.copyfile(src, os.path.join(unidad_dir, nombre))

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
            QMessageBox.warning(self, "Sin datos", "No hay fotos guardadas aún.")
            return
        destino_zip = os.path.join(self.root_dir, "masivo_fotos.zip")
        with ZipFile(destino_zip, "w") as zf:
            for root, _, files in os.walk(self.root_dir):
                # omite el propio zip si existe de alguna corrida anterior
                if root == self.root_dir:  # evita incluir zip antiguo
                    files = [f for f in files if not f.endswith(".zip")]
                for f in files:
                    abs_f = os.path.join(root, f)
                    rel_f = os.path.relpath(abs_f, self.root_dir)
                    zf.write(abs_f, rel_f)
        QMessageBox.information(self, "ZIP Final",
                                f"ZIP creado con todas las fotografías:\n{destino_zip}")

# ---------- módulo INDIVIDUAL (sin cambios en lógica previa) ----------
class IndividualApp(MasivoApp):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Módulo Individual")
        # ocultar botones NPN/Unidad y adaptar lógica
        self.btn_npn.setVisible(False)
        self.btn_unit.setVisible(False)
        self.btn_zip.setText("Generar ZIP")
        self.root_dir = None  # se definirá al seleccionar primera imagen

    def _guardar_npn(self):  # no usado
        pass
    def _guardar_unidad(self):  # no usado
        pass

    def create_zip_structure(self, npn, unidad, tipo):
        carpeta = os.path.join(self.root_dir, npn)
        os.makedirs(carpeta, exist_ok=True)
        if tipo == "Convencional":
            for k, src in self.clasificaciones.items():
                if src:
                    ext = os.path.splitext(src)[1]
                    nombre = f"{npn}_fachada{ext}" if k == "fachada" else f"{npn}_{unidad}_{k}{ext}"
                    shutil.copyfile(src, os.path.join(carpeta, nombre))
        else:
            shutil.copyfile(self.no_conv_fachada,
                os.path.join(carpeta, f"{npn}_fachada{os.path.splitext(self.no_conv_fachada)[1]}"))
            for i, src in enumerate(self.anexos, 1):
                ext = os.path.splitext(src)[1]
                nombre = f"{npn}_{unidad}_anexo{i}{ext}"
                shutil.copyfile(src, os.path.join(carpeta, nombre))
        return carpeta

    def _zip_final(self):
        if not self._campo_npn_unidad_ok():  # reuse from base
            return
        npn = self.inp_npn.text().strip()
        unidad = self.inp_unidad.text().strip()
        tipo = self.cmb_tipo.currentText()

        origen = self.clasificaciones["fachada"] or self.no_conv_fachada or (self.anexos[0] if self.anexos else None)
        if not origen:
            QMessageBox.warning(self, "Falta imagen", "Selecciona las imágenes antes.")
            return
        self.root_dir = os.path.dirname(origen)

        carpeta = self.create_zip_structure(npn, unidad, tipo)

        zip_path = os.path.join(self.root_dir, f"{npn}.zip")
        with ZipFile(zip_path, "w") as zf:
            for root, _, files in os.walk(carpeta):
                for f in files:
                    abs_f = os.path.join(root, f)
                    zf.write(abs_f, os.path.relpath(abs_f, os.path.dirname(carpeta)))
        QMessageBox.information(self, "ZIP creado", f"ZIP generado:\n{zip_path}")
        self._reset_unit_checks()

    # override botones
    def _zip_final(self):
        self.create_zip()

    def create_zip(self):
        if not self._campo_npn_unidad_ok():
            return
        npn = self.inp_npn.text().strip()
        unidad = self.inp_unidad.text().strip()
        tipo = self.cmb_tipo.currentText()
        origen = self.clasificaciones["fachada"] or self.no_conv_fachada or (self.anexos[0] if self.anexos else None)
        if not origen:
            QMessageBox.warning(self, "Falta imagen", "Selecciona las imágenes primero.")
            return
        self.root_dir = os.path.dirname(origen)
        carpeta = self.create_zip_structure(npn, unidad, tipo)
        zip_path = os.path.join(self.root_dir, f"{npn}.zip")
        with ZipFile(zip_path, "w") as zf:
            for root, _, files in os.walk(carpeta):
                for f in files:
                    zf.write(os.path.join(root, f), os.path.relpath(os.path.join(root, f), os.path.dirname(carpeta)))
        QMessageBox.information(self, "ZIP creado", f"ZIP generado:\n{zip_path}")
        self._reset_unit_checks()

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
