import arcpy
import pandas as pd
import os

# ------------------------------
# Leer archivo de mejoras
# ------------------------------
ruta_mejoras = r"D:\TRABAJO_MEJORAS_JESUS\consulta_mejoras.xlsx"
df_mejoras = pd.read_excel(ruta_mejoras)
df_mejoras.columns = [col.strip().lower().replace(" ", "_") for col in df_mejoras.columns]
df_mejoras["npn"] = df_mejoras["npn"].astype(str).str.strip()

# Leer los npn que fueron creados en el proceso anterior
ruta_excel_prueba = r"D:\TRABAJO_MEJORAS_JESUS\prueba.xlsx"
df_prueba = pd.read_excel(ruta_excel_prueba)
df_prueba.columns = [col.strip().lower().replace(" ", "_") for col in df_prueba.columns]
npns_creados = df_prueba["npn_cambio_rural_urbano"].astype(str).str.strip().unique().tolist()

# ------------------------------
# Capas
# ------------------------------
nombre_origen = "(LC) Unidad de Construcción"
nombre_destino = "(LC) Construcción"

aprx = arcpy.mp.ArcGISProject("CURRENT")
m = aprx.activeMap
capa_origen = [lyr for lyr in m.listLayers() if lyr.name == nombre_origen][0]
capa_destino = [lyr for lyr in m.listLayers() if lyr.name == nombre_destino][0]

path_origen = capa_origen.dataSource
path_destino = capa_destino.dataSource
workspace = os.path.dirname(os.path.dirname(path_destino))

# ------------------------------
# Campos destino a insertar
# ------------------------------
campos_insertar = [
    "SHAPE@", "codigo", "codigo_terreno", "id_construccion",
    "identificador", "tipo_construccion", "tipo_dominio",
    "numero_pisos", "numero_sotanos", "numero_mezanines",
    "numero_semisotanos", "anio_construccion",
    "area_construccion", "rural_urbano", "MEJORA"
]

# ------------------------------
# Insertar una vez por mejora (npn + identificador)
# ------------------------------
copiados = set()

with arcpy.da.Editor(workspace) as editor:
    with arcpy.da.SearchCursor(path_origen, ["SHAPE@", "codigo", "tipo_construccion", "rural_urbano", "identificador"]) as cursor_origen:
        with arcpy.da.InsertCursor(path_destino, campos_insertar) as cursor_destino:
            for row in cursor_origen:
                shape, npn, tipo_construccion, rural_urbano, identificador = row
                npn_str = str(npn).strip()
                identificador_str = str(identificador).strip()
                clave = f"{npn_str}_{identificador_str}"

                if npn_str in npns_creados and clave not in copiados:
                    datos_mejora = df_mejoras[(df_mejoras["npn"] == npn_str) & (df_mejoras["identificador"] == identificador_str)]
                    if not datos_mejora.empty:
                        total_pisos = int(datos_mejora["total_pisos"].values[0])
                        area_construida = float(datos_mejora["area_construida"].values[0])

                        nueva_fila = [
                            shape,
                            npn_str,
                            npn_str,       # codigo_terreno
                            None,          # id_construccion vacío
                            identificador_str,
                            tipo_construccion,
                            "Privado",     # tipo_dominio
                            total_pisos,
                            0,             # numero_sotanos
                            0,             # numero_mezanines
                            0,             # numero_semisotanos
                            2015,
                            area_construida,
                            rural_urbano,
                            None           # MEJORA vacío
                        ]
                        cursor_destino.insertRow(nueva_fila)
                        copiados.add(clave)

print("✅ Todas las mejoras copiadas correctamente a (LC) Construcción), sin duplicados por pisos ni identificadores.")
