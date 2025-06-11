import pandas as pd
import unicodedata

# Ruta del archivo original y de salida
archivo = r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTAS_CARTAGO_30_05\20250523_PREDIOS_CARTAGO_DESTINO_AJUSTAR.xlsx"
salida  = r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTAS_CARTAGO_30_05\20250523_PREDIOS_CARTAGO_DESTINO_AJUSTAR_FINAL.xlsx"

# Leer datos
df = pd.read_excel(archivo)
df.columns = df.columns.str.strip().str.lower()

# Normalizar texto
def normalizar(s):
    if pd.isna(s): return ""
    s = str(s).lower().strip()
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))

df["gestor_norm"] = df["destino_gestor"].apply(normalizar)
df["visitado_norm"] = df["visitados"].apply(normalizar)
df["municipio_norm"] = df["destino_municipio"].apply(normalizar)

# Hoja 1: resumen general con 'visitados'
hoja_1 = df[[
    "npn", "destino_gestor", "destino_municipio",
    "observacion", "no_visitados_valor_texto", "validacion_destino", "visitados"
]]

# Hoja 2: diferencias entre gestor y municipio
hoja_2 = df[df["gestor_norm"] != df["municipio_norm"]][[
    "npn", "destino_gestor", "destino_municipio"
]]

# Hoja 3: gestor vs validación
hoja_3 = df[["npn", "destino_gestor", "validacion_destino"]]

# Hoja 4: gestor vs visitado (dos tablas separadas horizontalmente)
tabla_izq = df[["npn", "destino_gestor", "visitados"]].reset_index(drop=True)
conflictos = df[df["gestor_norm"] != df["visitado_norm"]][["npn", "destino_gestor", "visitados"]].reset_index(drop=True)
tabla_der = conflictos.rename(columns={
    "npn": "npn_conflicto",
    "destino_gestor": "gestor_conflicto",
    "visitados": "visitado_conflicto"
}).reset_index(drop=True)

# Unir ambas con dos columnas vacías en el medio
tabla_final = pd.concat([
    tabla_izq,
    pd.DataFrame({"": [""] * max(len(tabla_izq), len(tabla_der)),
                  "  ": [""] * max(len(tabla_izq), len(tabla_der))}),
    tabla_der
], axis=1)

# Hoja 5: resumen cuantitativo
total = len(df)
coinciden_g_m = (df["gestor_norm"] == df["municipio_norm"]).sum()
diferencias_g_m = total - coinciden_g_m
coinciden_g_v = (df["gestor_norm"] == df["visitado_norm"]).sum()
diferencias_g_v = total - coinciden_g_v
nulos_gestor = df["destino_gestor"].isna().sum()
nulos_municipio = df["destino_municipio"].isna().sum()

resumen_df = pd.DataFrame({
    "Categoría": [
        "Total de registros",
        "Coincidencias entre gestor y municipio",
        "Diferencias entre gestor y municipio",
        "Coincidencias entre gestor y visitados",
        "Diferencias entre gestor y visitados",
        "Valores nulos en destino_gestor",
        "Valores nulos en destino_municipio"
    ],
    "Cantidad": [
        total,
        coinciden_g_m,
        diferencias_g_m,
        coinciden_g_v,
        diferencias_g_v,
        nulos_gestor,
        nulos_municipio
    ]
})

# Guardar todas las hojas en el archivo final
with pd.ExcelWriter(salida, engine="xlsxwriter") as writer:
    hoja_1.to_excel(writer, index=False, sheet_name="resumen_destinos")
    hoja_2.to_excel(writer, index=False, sheet_name="diferencias_gestor_mpio")
    hoja_3.to_excel(writer, index=False, sheet_name="gestor_vs_validacion")
    tabla_final.to_excel(writer, index=False, sheet_name="gestor_vs_visitado")
    resumen_df.to_excel(writer, index=False, sheet_name="resumen_cuantitativo")
