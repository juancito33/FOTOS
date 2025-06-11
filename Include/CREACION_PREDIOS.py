import arcpy
import pandas as pd
import math
import os

# ---------------------------------------
# BLOQUE 1 — Centroides y Excel de relaciones
# ---------------------------------------

capa_terrenos = "TERRENOS_SEBAS"
campo_codigo = "codigo"
centroides_por_codigo = {}

with arcpy.da.SearchCursor(capa_terrenos, ["SHAPE@", campo_codigo]) as cursor:
    for geom, codigo in cursor:
        if codigo:
            centroides_por_codigo[codigo] = geom.centroid

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

# ---------------------------------------
# BLOQUE 2 — Leer consulta_mejoras
# ---------------------------------------

ruta_mejoras = r"D:\TRABAJO_MEJORAS_JESUS\consulta_mejoras.xlsx"
df_mejoras = pd.read_excel(ruta_mejoras)
df_mejoras.columns = [col.strip().lower().replace(" ", "_") for col in df_mejoras.columns]
df_mejoras["npn"] = df_mejoras["npn"].astype(str).str.strip()
print("Columnas en consulta_mejoras:", df_mejoras.columns)

# ---------------------------------------
# BLOQUE 3 — Insertar con ajustes: 15m separación, rural_urbano, anexo
# ---------------------------------------

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

dx = 15  # ? Separación horizontal entre mejoras

with arcpy.da.Editor(workspace) as editor:
    with arcpy.da.InsertCursor(capa_destino, campos_salida) as cursor_out:
        for _, fila in df_validos.iterrows():
            centroide = centroides_por_codigo[fila["npn_terreno"]]
            npn_mejoras = str(fila["npn_cambio_rural_urbano"]).strip()

            mejoras_npns = df_mejoras[df_mejoras["npn"] == npn_mejoras].reset_index(drop=True)

            for indice_mejora, (_, mejora) in enumerate(mejoras_npns.iterrows()):
                npn = mejora["npn"]
                area_total = float(mejora["area_construida"])
                pisos = int(mejora["total_pisos"])
                uso = str(mejora["codigo"]).strip()
                uso_original = str(mejora["uso"])  # Para verificar si contiene (Anexo)
                identificador = mejora["identificador"]

                if pisos < 1:
                    pisos = 1

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

                    # ? Rural/Urbano basado en posiciones 5 y 6 del NPN
                    pos_5_6 = str(npn)[5:7]
                    rural_urbano = "Rural" if pos_5_6 == "00" else "Urbano"

                    # ? Tipo de construcción según campo uso (si contiene '(Anexo)')
                    tipo_construccion = "No Convencional" if "(Anexo)" in uso_original else "Convencional"

                    planta = f"Piso {piso + 1}"

                    row = [
                        poligono,
                        npn,
                        npn,
                        npn,
                        None,
                        rural_urbano,
                        uso,
                        planta,
                        tipo_construccion,
                        "Privado",
                        identificador
                    ]

                    cursor_out.insertRow(row)

print("? Polígonos insertados con separación de 15m y validaciones aplicadas.")