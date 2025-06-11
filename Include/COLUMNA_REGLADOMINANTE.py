import pandas as pd
import os

# ── 1. Rutas ───────────────────────────────────────────────
src  = r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTAS_CARTAGO_30_05\PREDIOS_JHONNY_CARTAGO_30_05.xlsx"
dst  = os.path.join(os.path.dirname(src),
                    "PREDIOS_JHONNY_CARTAGO_30_05_filled.xlsx")
sheet = "Hoja1"

# ── 2. Leer Hoja1 ───────────────────────────────────────────
df = pd.read_excel(src, sheet_name=sheet)

# Si prefieres, normaliza encabezados:
# df.columns = df.columns.str.strip().str.lower()

# ── 3. Rellenar categoria_dominante cuando esté vacía ──────
mask = (
    df["categoria_dominante"].isna() |            # NaN
    (df["categoria_dominante"].astype(str).str.strip() == "")  # cadena vacía
)

df.loc[mask, "categoria_dominante"] = df.loc[mask, "motivo_dest_npn"]

# ── 4. Guardar copia ────────────────────────────────────────
with pd.ExcelWriter(dst, engine="xlsxwriter") as w:
    df.to_excel(w, index=False, sheet_name=sheet)

print("✔️  Archivo generado:", dst)
