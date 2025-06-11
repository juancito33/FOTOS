import arcpy
import pandas as pd
import os

# Leer lista de npns válidos desde prueba.xlsx
ruta_excel_prueba = r"D:\TRABAJO_MEJORAS_JESUS\prueba.xlsx"
df_prueba = pd.read_excel(ruta_excel_prueba)
df_prueba.columns = [col.strip().lower().replace(" ", "_") for col in df_prueba.columns]
npns_validos = df_prueba["npn_cambio_rural_urbano"].astype(str).str.strip().unique().tolist()

# Capa origen y destino
nombre_origen = "(LC) Unidad de Construcción"
nombre_destino = "TERRENOS_SEBAS"

aprx = arcpy.mp.ArcGISProject("CURRENT")
m = aprx.activeMap
capa_origen = [l for l in m.listLayers() if l.name == nombre_origen][0]
capa_destino = [l for l in m.listLayers() if l.name == nombre_destino][0]

path_origen = capa_origen.dataSource
path_destino = capa_destino.dataSource
workspace = os.path.dirname(os.path.dirname(path_destino))

# Filtrar geometrias por npn válido
geometrias_por_npn = {}
with arcpy.da.SearchCursor(path_origen, ["SHAPE@", "codigo"]) as cursor:
    for shape, npn in cursor:
        npn_str = str(npn).strip()
        if npn_str in npns_validos:
            geometrias_por_npn.setdefault(npn_str, []).append(shape)

# Solo los campos que se deben llenar manualmente
campos_insertar = ["SHAPE@", "codigo", "codigo_man", "rural_urba", "resolucion"]

with arcpy.da.Editor(workspace):
    with arcpy.da.InsertCursor(path_destino, campos_insertar) as cursor:
        for npn, shapes in geometrias_por_npn.items():
            geom_unida = shapes[0]
            for shape in shapes[1:]:
                geom_unida = geom_unida.union(shape)

            rural = "Rural" if npn[5:7] == "00" else "Urbano"
            fila = [geom_unida, npn, npn[:17], rural, "SEBAS"]
            cursor.insertRow(fila)

# Luego puedes actualizar área y perímetro (opcional)
# arcpy.CalculateGeometryAttributes_management("TERRENOS_SEBAS", [["shape_area", "AREA"], ["shape_length", "PERIMETER_LENGTH"]])

print("✅ TERRENOS_SEBAS actualizado con geometrías unidas y campos preservados.")
