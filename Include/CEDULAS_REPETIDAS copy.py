import pandas as pd, unicodedata, itertools, os
from rapidfuzz import fuzz  # pip install rapidfuzz

# ───── 1 · Rutas
XLS_IN = r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTA_ALCALA\CEDULAS.xlsx"
SHEET = 0
OUT_DIR = os.path.dirname(XLS_IN)

XLS_REP = os.path.join(OUT_DIR, "cedulas_reporte.xlsx")
XLS_UNI = os.path.join(OUT_DIR, "cedulas_sin_dup.xlsx")
XLS_SIND = os.path.join(OUT_DIR, "cedulas_sin_documento.xlsx")
XLS_VAC = os.path.join(OUT_DIR, "cedulas_sin_nombre.xlsx")
XLS_ORG = os.path.join(OUT_DIR, "CEDULAS_organizado.xlsx")

STOP = {"de", "del", "la", "las", "los", "y"}

# ───── 2 · Helpers
def norm(t: str) -> str:
    t = "" if t is None else str(t)
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.lower().strip().split())

def soundex_es(w: str) -> str:
    w = norm(w)
    if not w:
        return ""
    mapa = {"b":1,"f":1,"p":1,"v":1,"c":2,"g":2,"j":2,"k":2,"q":2,"s":2,"x":2,"z":2,
            "d":3,"t":3,"l":4,"m":5,"n":5,"r":6}
    head = w[0]
    tail = [str(mapa.get(c, "")) for c in w[1:]]
    tail = [d for i, d in enumerate(tail) if i == 0 or d != tail[i - 1]]
    return (head + "".join(tail) + "000")[:4]

def tok_equiv(a, b, thr=80):
    return soundex_es(a) == soundex_es(b) or fuzz.token_set_ratio(a, b) >= thr

def grupo_similar(noms):
    for x, y in itertools.combinations(noms, 2):
        sx, sy = x.split(), y.split()
        short, long = (sx, sy) if len(sx) <= len(sy) else (sy, sx)
        if not all(any(tok_equiv(t, l) for l in long) for t in short):
            return False
    return True

# ───── 3 · Cargar archivo (hoja 0)
df = pd.read_excel(XLS_IN, sheet_name=SHEET,
                   dtype={"npn": str, "documento_identidad": str})
df.columns = df.columns.str.strip().str.lower()

for col in ["documento_identidad", "razon_social", "nombre",
            "primer_nombre", "segundo_nombre",
            "primer_apellido", "segundo_apellido"]:
    df[col] = df[col].fillna("").apply(norm)

# ───── 4 · Filas sin documento (nombre = "no registra")
sin_doc = df[df["documento_identidad"].eq("") & df["nombre"].eq("no registra")]
df = df.drop(sin_doc.index)

# ───── 5 · nombre_legal
df["nombre_legal"] = df.apply(
    lambda r: " ".join(filter(None, [r["primer_nombre"], r["segundo_nombre"],
                                     r["primer_apellido"], r["segundo_apellido"]])).strip()
    or r["razon_social"] or r["nombre"], axis=1)

# ───── 6 · Filas sin nombre
sin_nom = df[df["nombre_legal"].eq("")]
df = df.drop(sin_nom.index)

# ───── 7 · Duplicados vs únicos
dup_mask = df.duplicated("documento_identidad", keep=False)
df_dup, df_uni = df[dup_mask].copy(), df[~dup_mask].copy()

# ───── 8 · Clasificación
def clasifica(g):
    noms = g["nombre_legal"].unique().tolist()
    ap_equiv = all(tok_equiv(a, b) for a, b in itertools.combinations(
        g["primer_apellido"].unique(), 2)) if len(g) > 1 else True
    if len(noms) == 1:
        cat = "Mismo titular"
    elif ap_equiv and grupo_similar(noms):
        cat = "Error de digitación"
    else:
        cat = "Revisar"
    return pd.Series({"clasificacion": cat})

df_dup = df_dup.merge(
    df_dup.groupby("documento_identidad", as_index=False)
          .apply(clasifica, include_groups=False),
    on="documento_identidad"
)

df_uni["clasificacion"] = "Sin duplicado"
sin_doc["clasificacion"] = "Sin documento"
sin_nom["clasificacion"] = "Sin nombre"

# Asegurar npn presente
for d in [df_dup, df_uni, sin_doc, sin_nom]:
    if "npn" not in d.columns:
        d["npn"] = ""

df_org = pd.concat([df_dup, df_uni, sin_doc, sin_nom], ignore_index=True)\
           .sort_values(["documento_identidad", "nombre_legal", "npn"])

# ───── 9 · Resumen duplicados CON npn_asociados (solo para cálculo interno)
resumen = (df_dup.groupby(["documento_identidad", "clasificacion"], as_index=False)
                  .agg(registros=("npn", "size"),
                       npn_distintos=("npn", "nunique"),
                       variantes_nombre=("nombre_legal", "nunique"),
                       npn_asociados=("npn", lambda x: ", ".join(sorted(set(x.dropna()))))))

detalle = df_dup[df_dup["clasificacion"] == "Revisar"]

# ───── 10 · Exportar
with pd.ExcelWriter(XLS_REP, engine="xlsxwriter") as w:
    # Hoja de resumen sin npn_asociados
    resumen_simple = resumen.drop(columns=["npn_asociados"])
    resumen_simple.to_excel(w, index=False, sheet_name="duplicados_resumen")

    # Detalle de casos para revisión
    detalle.to_excel(w, index=False, sheet_name="detalle_revisar")

    # Crear hojas por clasificación (excepto Revisar)
    for clasif in df_dup["clasificacion"].unique():
        if clasif == "Revisar":
            continue
        subset = df_dup[df_dup["clasificacion"] == clasif]
        subset = subset[["documento_identidad", "nombre_legal", "npn"]]\
                       .sort_values(by=["documento_identidad", "npn"])
        hoja_nombre = f"npn_{clasif.lower().replace(' ', '_')[:25]}"
        subset.to_excel(w, index=False, sheet_name=hoja_nombre)

df_uni.to_excel(XLS_UNI, index=False, sheet_name="documentos_unicos")
if not sin_doc.empty:
    sin_doc.to_excel(XLS_SIND, index=False, sheet_name="sin_documento")
if not sin_nom.empty:
    sin_nom.to_excel(XLS_VAC, index=False, sheet_name="sin_nombre")
df_org.to_excel(XLS_ORG, index=False, sheet_name="organizado")

print("Flujo 3 ejecutado:")
print("→", XLS_REP)
print("→", XLS_UNI)
print("→", XLS_ORG)
if not sin_doc.empty: print("→", XLS_SIND)
if not sin_nom.empty: print("→", XLS_VAC)
