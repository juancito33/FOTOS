import arcpy
import pandas as pd
import math
import os
import numpy as np

# ---------------------------------------
# BLOQUE 1 — Crear polígonos separados 15m en (LC) Unidad de Construcción
# ---------------------------------------

capa_terrenos = "(LC) Terreno"
campo_codigo = "codigo"
centroides_por_codigo = {}

with arcpy.da.SearchCursor(capa_terrenos, ["SHAPE@", campo_codigo]) as cursor:
    for geom, codigo in cursor:
        if codigo:
            centroides_por_codigo[str(codigo).strip()] = geom.centroid

# Obtener sistema de referencia espacial
sr = arcpy.Describe(capa_terrenos).spatialReference
print(f"Centroides leídos: {len(centroides_por_codigo)}")

# Leer archivo prueba.xlsx
ruta_excel_prueba = r"D:\TRABAJO_MEJORAS_JESUS\prueba.xlsx"
df_prueba = pd.read_excel(ruta_excel_prueba)
df_prueba.columns = [col.strip().lower().replace(" ", "_") for col in df_prueba.columns]
df_prueba = df_prueba.rename(columns={"npn_terrejo_mejoras": "npn_terreno"})
df_validos = df_prueba[df_prueba["npn_terreno"].isin(centroides_por_codigo.keys())]
print(f"Coincidencias válidas: {len(df_validos)}")

# Leer archivo consulta_mejoras.xlsx
ruta_mejoras = r"D:\TRABAJO_MEJORAS_JESUS\consulta_mejoras.xlsx"
df_mejoras = pd.read_excel(ruta_mejoras)
df_mejoras.columns = [col.strip().lower().replace(" ", "_") for col in df_mejoras.columns]
df_mejoras["npn"] = df_mejoras["npn"].astype(str).str.strip()

# Crear polígonos en capa destino
nombre_capa_destino = "(LC) Unidad de Construcción"
aprx = arcpy.mp.ArcGISProject("CURRENT")
m = aprx.activeMap
layer = [lyr for lyr in m.listLayers() if lyr.name == nombre_capa_destino][0]
capa_destino = layer.dataSource
workspace = os.path.dirname(os.path.dirname(capa_destino))

campos_salida = [
    "SHAPE@", "codigo", "codigo_construccion", "codigo_terreno",
    "id_unidad_construccion", "rural_urbano", "uso", "planta",
    "tipo_construccion", "tipo_dominio", "identificador"
]

dx = 15

with arcpy.da.Editor(workspace) as editor:
    with arcpy.da.InsertCursor(capa_destino, campos_salida) as cursor_out:
        for _, fila in df_validos.iterrows():
            centroide = centroides_por_codigo[fila["npn_terreno"]]
            npn_mejoras = str(fila["npn_cambio_rural_urbano"]).strip()
            mejoras_npns = df_mejoras[df_mejoras["npn"] == npn_mejoras].reset_index(drop=True)

            for indice_mejora, (_, mejora) in enumerate(mejoras_npns.iterrows()):
                npn = str(mejora["npn"]).strip()
                area_total = float(mejora["area_construida"])

                try:
                    pisos = int(mejora["total_pisos"])
                    if pisos < 1:
                        pisos = 1
                except:
                    pisos = 1

                uso = str(mejora["codigo"]).strip()
                uso_original = str(mejora["uso"])
                identificador = mejora["identificador"]

                area_por_piso = area_total / pisos
                lado = math.sqrt(area_por_piso)

                x0 = centroide.X + (indice_mejora * dx)
                y0 = centroide.Y
                mitad = lado / 2

                for piso in range(pisos):
                    array = arcpy.Array([
                        arcpy.Point(x0 - mitad, y0 - mitad),
                        arcpy.Point(x0 - mitad, y0 + mitad),
                        arcpy.Point(x0 + mitad, y0 + mitad),
                        arcpy.Point(x0 + mitad, y0 - mitad),
                        arcpy.Point(x0 - mitad, y0 - mitad)
                    ])
                    poligono = arcpy.Polygon(array, sr)

                    pos_5_6 = npn[5:7]
                    rural_urbano = "Rural" if pos_5_6 == "00" else "Urbano"
                    tipo_construccion = "No Convencional" if "(Anexo)" in uso_original else "Convencional"
                    planta = f"Piso {piso + 1}"

                    row = [
                        poligono, npn, npn, npn, None, rural_urbano, uso,
                        planta, tipo_construccion, "Privado", identificador
                    ]
                    cursor_out.insertRow(row)

print("? Paso 1: Polígonos insertados en (LC) Unidad de Construcción.")

# ---------------------------------------
# BLOQUE 2 — Copiar a (LC) Construcción
# ---------------------------------------

nombre_destino_construccion = "(LC) Construcción"
capa_destino_construccion = [lyr for lyr in m.listLayers() if lyr.name == nombre_destino_construccion][0]
path_destino_construccion = capa_destino_construccion.dataSource

campos_insertar = [
    "SHAPE@", "codigo", "codigo_terreno", "id_construccion",
    "identificador", "tipo_construccion", "tipo_dominio",
    "numero_pisos", "numero_sotanos", "numero_mezanines",
    "numero_semisotanos", "anio_construccion",
    "area_construccion", "rural_urbano", "MEJORA"
]

copiados = set()

with arcpy.da.Editor(workspace) as editor:
    with arcpy.da.SearchCursor(capa_destino, ["SHAPE@", "codigo", "tipo_construccion", "rural_urbano", "identificador"]) as cursor_origen:
        with arcpy.da.InsertCursor(path_destino_construccion, campos_insertar) as cursor_destino:
            for row in cursor_origen:
                shape, npn, tipo_construccion, rural_urbano, identificador = row
                npn_str = str(npn).strip()
                identificador_str = str(identificador).strip()
                clave = f"{npn_str}_{identificador_str}"

                if clave not in copiados:
                    datos_mejora = df_mejoras[(df_mejoras["npn"] == npn_str) & (df_mejoras["identificador"] == identificador_str)]
                    if not datos_mejora.empty:
                        try:
                            total_pisos = int(datos_mejora["total_pisos"].values[0])
                            if total_pisos < 1:
                                total_pisos = 1
                        except:
                            total_pisos = 1
                        area_construida = float(datos_mejora["area_construida"].values[0])

                        nueva_fila = [
                            shape, npn_str, npn_str, None, identificador_str,
                            tipo_construccion, "Privado", total_pisos, 0, 0, 0,
                            2015, area_construida, rural_urbano, None
                        ]
                        cursor_destino.insertRow(nueva_fila)
                        copiados.add(clave)

print("? Paso 2: Mejoras copiadas correctamente a (LC) Construcción.")