import pandas as pd, unicodedata, os, warnings, time, numpy as np
warnings.filterwarnings("ignore", category=DeprecationWarning)

# ───────────  Helper de tiempo
T0=time.time(); lap=lambda m:print(f"{m:<62}{round(time.time()-T0,2)} s")

# ───────────  Normalizador
def norm(txt:str)->str:
    t=unicodedata.normalize("NFKD",str(txt))
    t="".join(c for c in t if not unicodedata.combining(c))
    return " ".join(t.lower().strip().split())

# ───────────  Rutas
XLSX=r"D:\TRABAJO_VA_GEOINFORMATCA\CONSULTA_ALCALA\RESULTADOS_CONSULTAS\predios_destinos.xlsx"
OUT =os.path.dirname(XLSX)
OK  =os.path.join(OUT,"validos_npn_AREA_ALCALA.xlsx")
BAD =os.path.join(OUT,"inconsistentes_npn_AREA_ALCALA.xlsx")

lap("INICIO")

# ─────────── 1· Cargar
df=pd.read_excel(XLSX,dtype={"npn":str,"destino":str})
df.columns=df.columns.str.strip().str.lower()
df.rename(columns={"área_construida":"area_construida"},inplace=True)
df["area_num"]=pd.to_numeric(df.area_construida,errors="coerce").fillna(0)
lap(f"Filas cargadas: {len(df):,}")

# ─────────── 2· alfa duplicado
dup=df.duplicated(["npn","resolucion_predio_id","alfa_carto_id"],keep=False)
df["ok_alfa"]=~dup
lap(f"alfa_carto_id duplicados: {dup.sum():,}")

# ─────────── 3· Reglas de destino
AUTO_VALID={norm(x) for x in (
    "pecuario recreacional uso publico servicios funerales "
    "forestal infraestructura transporte agricola agropecuario").split()}

LOTES_RULE=("no convencional","solo_nc")   # (tipo_req, marcador especial)

RULES={
 "habitacional":("convencional",">=1"),"comercial":("convencional",">=1"),
 "industrial":("convencional",">=1"),"educativo":("convencional",">=1"),
 "institucional":("convencional",">=1"),"acuicola":("no convencional",">=1"),
 "agroindustrial":("convencional",">=1"),
 "infraestructura hidraulica":("convencional",">=1"),
 "religioso":("convencional",">=1"),"salubridad":("convencional",">=1"),
 "servicios especiales":("convencional",">=1")}
RULES={norm(k):v for k,v in RULES.items()}

def chk_dest(g):
    raw=str(g.destino.iloc[0]).strip(); dst=norm(raw)
    if dst in AUTO_VALID:
        return pd.Series({"ok_destino":True,"motivo_dest":""})

    tipo_req, area_rule = LOTES_RULE if "lote" in dst else RULES.get(dst,(None,None))
    if tipo_req is None:
        return pd.Series({"ok_destino":False,"motivo_dest":f"sin regla '{raw}'"})

    motives=[]
    rows_area=g[g.area_num>0]

    # ----- comportamiento especial para LOTES -----
    if "lote" in dst:
        if rows_area.empty:
            pass  # lote vacío → válido
        else:
            # cada fila con área debe ser No Convencional O un Anexo
            def fila_ok(r):
                tipo_ok = str(r["tipo"]).lower()=="no convencional"
                anexo_ok = str(r.get("destino_regla","")).lower().startswith("anexo")
                return tipo_ok or anexo_ok
            if not rows_area.apply(fila_ok, axis=1).all():
                motives.append("área debe ser 'No Convencional' o Anexo")
    # ----- destinos convencionales -----
    else:
        if area_rule==">=1" and rows_area.empty:
            motives.append("requiere área > 0")
        if tipo_req and not g.tipo.str.lower().eq(tipo_req).any():
            motives.append(f"falta tipo {tipo_req}")

    return pd.Series({"ok_destino":not motives,"motivo_dest":"; ".join(motives)})

lap("Evaluando destinos…")
dest_info=df.groupby(["npn","resolucion_predio_id"],as_index=False).apply(chk_dest)
df=df.merge(dest_info,on=["npn","resolucion_predio_id"])
lap(f"Errores destino: {(~df.ok_destino).sum():,}")

# ─────────── 4· Dominante (salta anexos, omite si sin cat_dom)
if "destino_regla" in df.columns:
    lap("Calculando dominante…")
    df["cat"]=df.destino_regla.str.split(".").str[0].str.lower().replace({"residencial":"habitacional"})
    df["dest_norm"]=df.destino.map(norm)
    ordered=df.sort_values(["npn","area_num"],ascending=[True,False])

    def dom(sub):
        first=sub["cat"].iloc[0]
        if first!="anexo":
            return first
        non=sub.loc[sub["cat"]!="anexo","cat"]
        return non.iloc[0] if not non.empty else "anexo"

    dom_df=ordered.groupby("npn",as_index=False)\
                  .apply(lambda s: pd.Series({"cat_dom":dom(s)}))
    df=df.merge(dom_df,on="npn",how="left")

    EQUIV={
        "habitacional":{"habitacional"},"agropecuario":{"agricola","pecuario"},
        "comercial":{"comercial"},"industrial":{"industrial"},
        "institucional":{"institucional","educativo"},
        "educativo":{"educativo","institucional"}}

    df["ok_dom"]=df.apply(
        lambda r: True if pd.isna(r.cat_dom)            # sin categorías → no aplica
        else True if r.cat_dom=="anexo"                 # anexo → pasa
        else r.cat_dom in EQUIV.get(r.dest_norm,{r.dest_norm}), axis=1)
    df["motivo_dom_area"]=df.apply(
        lambda r:"" if r.ok_dom else "destino ≠ dominante",axis=1)
    lap(f"Predios con destino ≠ dominante: {(~df.ok_dom).sum():,}")
else:
    df["ok_dom"]=True; df["motivo_dom_area"]=""; df["cat_dom"]=None
    lap("destino_regla ausente — omito dominante")

# ─────────── 5· Resumen y exportar
df["fila_valida"]=df.ok_alfa & df.ok_destino & df.ok_dom
join=lambda s:"; ".join(sorted({x for x in s if x}))

res=(df.groupby("npn",as_index=False)
        .agg(
          unidades_total=('npn','size'),
          unidades_validas=('fila_valida','sum'),
          destinos=('destino',lambda x:", ".join(sorted(set(x)))),
          motivo_dest_npn=('motivo_dest',join),
          motivo_dom_area_npn=('motivo_dom_area',join),
          categoria_dominante=('cat_dom','first'),
          ok_dom_npn=('ok_dom','any')))
res["npn_valido"]=res.unidades_validas>=1
res["motivo_total"]=(res.motivo_dest_npn+"; "+res.motivo_dom_area_npn)\
                    .str.strip("; ").str.replace(";;",";").str.strip("; ")

lap("Resumen generado")

validos=res[res.npn_valido].drop(columns=["npn_valido"])
bad=res[~res.npn_valido]
sin_dom=bad[(~bad.ok_dom_npn)&(bad.categoria_dominante.isna())]

lap("Exportando Excel…")
with pd.ExcelWriter(OK,engine="xlsxwriter") as w:
    validos.to_excel(w,index=False,sheet_name="validos")
with pd.ExcelWriter(BAD,engine="xlsxwriter") as w:
    bad.to_excel(w,index=False,sheet_name="inconsistentes")
    if not sin_dom.empty:
        sin_dom.to_excel(w,index=False,sheet_name="sin_dominante")

lap("FIN — Archivos exportados")
