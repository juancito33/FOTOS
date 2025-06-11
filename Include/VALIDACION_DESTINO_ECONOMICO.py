"""
VALIDACION_CARTAGO.py
Clasifica NPN de la hoja 3 de AREAS_CARTAAAAAA.xlsx.

• Una fila es válida si:
  1) area_construida > 0 → tipo NO nulo
  2) alfa_carto_id único dentro de (npn, resolucion_predio_id)
  3) Destino:
       – AUTO_VALID  → siempre válido
       – contiene 'lote' (tras normalizar) → regla estricta LOTES_RULE
       – demás → REGLAS_DESTINO

Un NPN es válido si ≥ 1 fila es válida.

Resultados: validos_npn.xlsx · inconsistentes_npn.xlsx
"""

import pandas as pd, unicodedata, os, warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# ----------------------------------------------------------- #
# 1 · utilidades
# ----------------------------------------------------------- #
def normalize_dest(text: str) -> str:
    """
    Quita tildes, pasa a minúsculas y colapsa espacios.
    Ej.: 'Agrícola ' → 'agricola'
    """
    txt = unicodedata.normalize("NFKD", text)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return " ".join(txt.lower().strip().split())

# ----------------------------------------------------------- #
# 2 · Rutas y parámetros
# ----------------------------------------------------------- #
XLSX_PATH = r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTAS_CARTAGO_30_05\NO_VISITADOS.xlsx"
SHEET_IDX = 0
OUT_DIR   = os.path.dirname(XLSX_PATH)

VALID_XLS = os.path.join(OUT_DIR, "validos_npn.xlsx")
BAD_XLS   = os.path.join(OUT_DIR, "inconsistentes_npn.xlsx")

# ----------------------------------------------------------- #
# 3 · Destinos auto-válidos y reglas
# ----------------------------------------------------------- #
AUTO_VALID = {
    "pecuario", "recreacional", "uso publico", "servicios funerales",
    "forestal", "infraestructura transporte", "agricola", "agropecuario",
}

LOTES_RULE = {"area": "solo_nc", "tipo": "No Convencional"}

REGLAS_DESTINO = {
    "acuicola":                  {"area": ">=1", "tipo": "No Convencional"},
    "agroindustrial":            {"area": ">=1", "tipo": "Convencional"},
    "comercial":                 {"area": ">=1", "tipo": "Convencional"},
    "educativo":                 {"area": ">=1", "tipo": "Convencional"},
    "habitacional":              {"area": ">=1", "tipo": "Convencional"},
    "industrial":                {"area": ">=1", "tipo": "Convencional"},
    "infraestructura hidraulica":{"area": ">=1", "tipo": "Convencional"},
    "institucional":             {"area": ">=1", "tipo": "Convencional"},
    "religioso":                 {"area": ">=1", "tipo": "Convencional"},
    "salubridad":                {"area": ">=1", "tipo": "Convencional"},
    "servicios especiales":      {"area": ">=1", "tipo": "Convencional"},
}

# Normalizamos también las claves de REGLAS_DESTINO
REGLAS_DESTINO = {normalize_dest(k): v for k, v in REGLAS_DESTINO.items()}
AUTO_VALID_NORM = {normalize_dest(x) for x in AUTO_VALID}

# ----------------------------------------------------------- #
# 4 · Cargar datos
# ----------------------------------------------------------- #
df = pd.read_excel(
    XLSX_PATH, sheet_name=SHEET_IDX,
    dtype={"npn": str, "destino": str}
)
df.columns = df.columns.str.strip().str.lower()
df.rename(columns={"área_construida": "area_construida"}, inplace=True)

# ----------------------------------------------------------- #
# 5 · Regla fila: área / tipo
# ----------------------------------------------------------- #
df["ok_area_tipo"] = ~(df["area_construida"].notna() & df["tipo"].isna())

# ----------------------------------------------------------- #
# 6 · alfa_carto_id único
# ----------------------------------------------------------- #
def eval_alfa(g):
    dup = g["alfa_carto_id"].dropna().duplicated().any()
    g["ok_alfa"] = not dup
    g["motivo_alfa"] = "" if not dup else "alfa_carto_id duplicado"
    return g

df = (
    df.groupby(["npn", "resolucion_predio_id"], dropna=False)
      .apply(eval_alfa, include_groups=False)
      .reset_index(names=["npn", "resolucion_predio_id", "idx_orig"])
      .drop(columns="idx_orig")
)

# ----------------------------------------------------------- #
# 7 · Regla destino
# ----------------------------------------------------------- #
def eval_destino(g):
    dest_raw = str(g["destino"].iloc[0]).strip()
    dest_norm = normalize_dest(dest_raw)

    # Destinos auto-válidos
    if dest_norm in AUTO_VALID_NORM:
        g["ok_destino"] = True
        g["motivo_dest"] = ""
        return g

    # Destinos tipo lote
    if "lote" in dest_norm:
        rule = LOTES_RULE
    else:
        rule = REGLAS_DESTINO.get(dest_norm)

    if rule is None:
        g["ok_destino"] = False
        g["motivo_dest"] = f"destino '{dest_raw}' sin regla"
        return g

    motivos = []
    has_area = (g["area_construida"].fillna(0) > 0).any()

    if rule["area"] == ">=1" and not has_area:
        motivos.append("requiere área > 0")
    elif rule["area"] == "solo_nc":
        if has_area:
            con_area = g[g["area_construida"].fillna(0) > 0]
            if not (con_area["tipo"].str.lower() == "no convencional").all():
                motivos.append("toda fila con área debe ser No Convencional")

    tipo_req = rule["tipo"]
    if tipo_req and "lote" not in dest_norm:
        if not (g["tipo"].str.lower() == tipo_req.lower()).any():
            motivos.append(f"debe tener tipo {tipo_req}")

    g["ok_destino"] = len(motivos) == 0
    g["motivo_dest"] = "; ".join(motivos)
    return g

df = (
    df.groupby(["npn", "resolucion_predio_id"], dropna=False)
      .apply(eval_destino, include_groups=False)
      .reset_index(names=["npn", "resolucion_predio_id", "idx_orig"])
      .drop(columns="idx_orig")
)

# ----------------------------------------------------------- #
# 8 · Resultado por fila y motivos
# ----------------------------------------------------------- #
df["fila_valida"] = df["ok_area_tipo"] & df["ok_alfa"] & df["ok_destino"]

def mot_row(r):
    out=[]
    if not r["ok_area_tipo"]: out.append("área sin tipo")
    if not r["ok_alfa"]:      out.append(r["motivo_alfa"])
    if not r["ok_destino"]:   out.append(r["motivo_dest"])
    return "; ".join(out)

df["motivo_fila"] = df.apply(mot_row, axis=1)

# ----------------------------------------------------------- #
# 9 · Agregado por NPN
# ----------------------------------------------------------- #
def agg_mot(s): return "; ".join(sorted({x for x in s if x}))

resumen = (
    df.groupby("npn", as_index=False)
      .agg(
          unidades_total   = ('npn', 'size'),
          unidades_validas = ('fila_valida', 'sum'),
          destinos         = ('destino', lambda x: ", ".join(sorted(set(x)))),
          motivo_npn       = ('motivo_fila', agg_mot)
      )
)
resumen["npn_valido"] = resumen["unidades_validas"] >= 1

# ----------------------------------------------------------- #
# 10 · Exportar
# ----------------------------------------------------------- #
validos = resumen[resumen["npn_valido"]].drop(columns=["npn_valido", "motivo_npn"])
inconsistentes = resumen[~resumen["npn_valido"]].drop(columns=["npn_valido"])

with pd.ExcelWriter(VALID_XLS, engine="xlsxwriter") as w:
    validos.to_excel(w, index=False, sheet_name="npn_validos_CARTAGO_NO_VISITADOS")

with pd.ExcelWriter(BAD_XLS, engine="xlsxwriter") as w:
    inconsistentes.to_excel(w, index=False, sheet_name="npn_inconsistentes_CARTAGO_NO_VISITADOS")

print("¡Proceso terminado! Se generaron validos_npn.xlsx e inconsistentes_npn.xlsx.")
