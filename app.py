import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
from datetime import date, datetime, timedelta
import uuid

# ── CONFIG ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MHO — Multi Herrajes Oriente",
    page_icon="🔩",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CONEXIÓN SUPABASE ─────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_PUBLISHABLE_KEY"]
    return create_client(url, key)

sb = get_supabase()

# ── HELPERS ───────────────────────────────────────────────────────────────────
def success(msg): st.toast(f"✅ {msg}", icon="✅")
def error(msg):   st.toast(f"❌ {msg}", icon="❌")
def warn(msg):    st.toast(f"⚠️ {msg}", icon="⚠️")

def fmt_usd(val):
    try: return f"${float(val):,.2f}"
    except: return "$0.00"

def get_productos():
    r = sb.table("dim_productos").select("*").order("categoria").order("descripcion").execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def get_clientes():
    r = sb.table("dim_clientes").select("*").order("nombre").execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def get_proveedores():
    r = sb.table("dim_proveedores").select("*").order("nombre").execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def get_ventas():
    r = sb.table("fact_ventas").select("*, dim_clientes(nombre)").order("fecha", desc=True).execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def get_venta_items(venta_id):
    r = sb.table("fact_venta_items").select("*, dim_productos(codigo, descripcion, precio_costo)").eq("venta_id", venta_id).execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def get_todas_venta_items():
    r = sb.table("fact_venta_items").select("*, dim_productos(codigo, descripcion, precio_costo), fact_ventas(fecha, estado)").execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def get_pedidos():
    r = sb.table("fact_pedidos").select("*, dim_proveedores(nombre)").order("fecha", desc=True).execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def get_pedido_items(pedido_id):
    r = sb.table("fact_pedido_items").select("*, dim_productos(codigo, descripcion)").eq("pedido_id", pedido_id).execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def get_movimientos():
    r = sb.table("fact_movimientos").select("*").order("fecha", desc=True).execute()
    return pd.DataFrame(r.data) if r.data else pd.DataFrame()

def ensure_fecha(f):
    r = sb.table("dim_tiempo").select("fecha").eq("fecha", str(f)).execute()
    if not r.data:
        d = date.fromisoformat(str(f)) if isinstance(f, str) else f
        sb.table("dim_tiempo").insert({
            "fecha": str(d), "anio": d.year, "mes": d.month, "dia": d.day,
            "mes_nombre": d.strftime("%B"), "trimestre": f"Q{(d.month-1)//3+1}"
        }).execute()

def registrar_movimiento(tipo, categoria, monto, fecha, descripcion, ref_id=None):
    ensure_fecha(fecha)
    sb.table("fact_movimientos").insert({
        "id": str(uuid.uuid4()), "fecha": str(fecha), "tipo": tipo,
        "categoria": categoria, "monto": float(monto),
        "descripcion": descripcion,
        "referencia_id": str(ref_id) if ref_id else None
    }).execute()

def calcular_profit_items(items_df):
    """Calcula profit por item usando precio_costo actual del producto."""
    if items_df.empty:
        return items_df
    def get_costo(row):
        prod = row.get("dim_productos")
        if isinstance(prod, dict):
            return float(prod.get("precio_costo", 0))
        return 0.0
    items_df = items_df.copy()
    items_df["costo_unit"] = items_df.apply(get_costo, axis=1)
    items_df["costo_total"] = items_df["costo_unit"] * items_df["cantidad"]
    items_df["profit"] = items_df["subtotal"] - items_df["costo_total"]
    items_df["margen_pct"] = items_df.apply(
        lambda r: (r["profit"] / r["costo_total"] * 100) if r["costo_total"] > 0 else 0, axis=1)
    return items_df

def filtrar_por_periodo(df, col_fecha, periodo):
    hoy = date.today()
    if periodo == "Esta semana":
        inicio = hoy - timedelta(days=hoy.weekday())
    elif periodo == "Este mes":
        inicio = hoy.replace(day=1)
    elif periodo == "Este año":
        inicio = hoy.replace(month=1, day=1)
    else:
        return df
    df = df.copy()
    df[col_fecha] = pd.to_datetime(df[col_fecha]).dt.date
    return df[df[col_fecha] >= inicio]

# ── ESTILOS ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.6rem !important; }
[data-testid="stMetricLabel"] { font-size: 0.85rem !important; color: #888; }
.stTabs [data-baseweb="tab"] { font-size: 1rem; padding: 8px 20px; }
div[data-testid="stExpander"] { border: 1px solid #333; border-radius: 8px; }
.profit-box { background: #1a2e1a; border: 1px solid #2d6a3f; border-radius: 8px;
              padding: 1rem; margin-top: 0.5rem; }
.profit-row { display: flex; justify-content: space-between; font-size: 13px;
              padding: 4px 0; border-bottom: 1px solid #2d3a2d; }
</style>
""", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    import os
    if os.path.exists("logo.png"):
        st.image("logo.png", width=110)
    else:
        st.image("https://img.icons8.com/ios-filled/100/wrench.png", width=48)
    st.title("Multi Herrajes Oriente")
    st.caption("Sistema de inventario · MHO")
    st.divider()
    pagina = st.radio("Navegación", [
        "🏠 Dashboard",
        "📦 Inventario",
        "🛒 Nueva Venta",
        "📋 Historial Ventas",
        "🚚 Pedidos",
        "👥 Clientes",
        "💰 Finanzas",
        "📤 Exportar datos",
    ], label_visibility="collapsed")
    st.divider()
    st.caption(f"📅 {date.today().strftime('%d/%m/%Y')}")

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if pagina == "🏠 Dashboard":
    st.title("🏠 Dashboard")

    productos_df = get_productos()
    ventas_df    = get_ventas()
    movs_df      = get_movimientos()

    # ── Filtro de período ──────────────────────────────────────────────────
    periodo = st.radio("Período", ["Esta semana", "Este mes", "Este año", "Todo"],
                       horizontal=True, key="dash_periodo")

    st.divider()

    # ── Calcular profit del período ───────────────────────────────────────
    todos_items = get_todas_venta_items()

    def calcular_kpis_periodo(ventas_df, todos_items, movs_df, periodo):
        if ventas_df.empty:
            return 0, 0, 0, 0, 0
        v = ventas_df[ventas_df["estado"] == "Completada"].copy()
        if periodo != "Todo":
            v = filtrar_por_periodo(v, "fecha", periodo)
        ingresos_p = v["total"].sum() if not v.empty else 0
        n_ventas_p = len(v)

        # Profit: cruzar con items del período
        profit_p = 0
        costo_p  = 0
        if not todos_items.empty and not v.empty:
            venta_ids = set(v["id"].tolist())
            items_p = todos_items[todos_items["venta_id"].isin(venta_ids)].copy()
            if not items_p.empty:
                items_p = calcular_profit_items(items_p)
                profit_p = items_p["profit"].sum()
                costo_p  = items_p["costo_total"].sum()

        # Egresos del período
        if not movs_df.empty:
            eg = movs_df[movs_df["tipo"] == "egreso"].copy()
            if periodo != "Todo":
                eg = filtrar_por_periodo(eg, "fecha", periodo)
            egresos_p = eg["monto"].sum() if not eg.empty else 0
        else:
            egresos_p = 0

        return ingresos_p, profit_p, costo_p, n_ventas_p, egresos_p

    ingresos_p, profit_p, costo_p, n_ventas_p, egresos_p = calcular_kpis_periodo(
        ventas_df, todos_items, movs_df, periodo)

    margen_p = (profit_p / costo_p * 100) if costo_p > 0 else 0

    # ── KPIs principales ──────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💵 Ingresos", fmt_usd(ingresos_p))
    c2.metric("💚 Profit bruto", fmt_usd(profit_p))
    c3.metric("📊 Margen", f"{margen_p:.1f}%")
    c4.metric("🛒 Ventas", n_ventas_p)
    c5.metric("📤 Egresos", fmt_usd(egresos_p))

    st.divider()

    col1, col2 = st.columns([2, 1])

    with col1:
        # Gráfico profit vs ingresos por mes
        if not todos_items.empty and not ventas_df.empty:
            v_comp = ventas_df[ventas_df["estado"] == "Completada"].copy()
            if not v_comp.empty:
                items_graf = todos_items[todos_items["venta_id"].isin(v_comp["id"])].copy()
                if not items_graf.empty:
                    items_graf = calcular_profit_items(items_graf)
                    # Unir con fecha de venta
                    fecha_map = v_comp.set_index("id")["fecha"].to_dict()
                    items_graf["fecha_venta"] = items_graf["venta_id"].map(fecha_map)
                    items_graf["mes"] = pd.to_datetime(items_graf["fecha_venta"]).dt.strftime("%Y-%m")
                    por_mes = items_graf.groupby("mes").agg(
                        ingresos=("subtotal","sum"),
                        profit=("profit","sum"),
                        costo=("costo_total","sum")
                    ).reset_index()

                    fig = go.Figure()
                    fig.add_bar(x=por_mes["mes"], y=por_mes["ingresos"],
                                name="Ingresos", marker_color="#d4860a")
                    fig.add_bar(x=por_mes["mes"], y=por_mes["profit"],
                                name="Profit", marker_color="#2d9955")
                    fig.add_bar(x=por_mes["mes"], y=por_mes["costo"],
                                name="Costo", marker_color="#555555")
                    fig.update_layout(
                        barmode="group", title="Ingresos / Profit / Costo por mes",
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        legend=dict(orientation="h", y=1.1),
                        margin=dict(l=0,r=0,t=40,b=0))
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin datos de ventas para graficar.")

        # Ventas recientes
        st.subheader("📋 Ventas recientes")
        if not ventas_df.empty:
            recent = ventas_df.head(8).copy()
            recent["cliente"] = recent["dim_clientes"].apply(
                lambda x: x["nombre"] if isinstance(x, dict) else "Cliente directo")
            recent["total_fmt"] = recent["total"].apply(fmt_usd)
            st.dataframe(
                recent[["fecha","cliente","total_fmt","estado"]].rename(columns={
                    "fecha":"Fecha","cliente":"Cliente","total_fmt":"Total","estado":"Estado"}),
                use_container_width=True, hide_index=True)
        else:
            st.info("Sin ventas registradas aún.")

    with col2:
        # Top productos por profit — solo ventas completadas
        st.subheader("🏆 Top por profit")
        if not todos_items.empty and not ventas_df.empty:
            ids_completadas = set(ventas_df[ventas_df["estado"]=="Completada"]["id"].tolist())
            top_items = todos_items[todos_items["venta_id"].isin(ids_completadas)].copy()
            if not top_items.empty:
                top_items = calcular_profit_items(top_items)
                top_items["producto"] = top_items["dim_productos"].apply(
                    lambda x: x["codigo"] if isinstance(x, dict) else "—")
                top = top_items.groupby("producto")["profit"].sum().sort_values(ascending=False).head(8)
                for cod, pft in top.items():
                    st.write(f"**{cod}** — {fmt_usd(pft)}")
            else:
                st.info("Sin ventas completadas aún.")
        else:
            st.info("Sin ventas.")

        st.divider()

        # Alertas de stock
        st.subheader("⚠️ Stock bajo")
        if not productos_df.empty:
            bajos = productos_df[productos_df["stock_actual"] <= productos_df["stock_minimo"]]
            if not bajos.empty:
                for _, p in bajos.iterrows():
                    color = "🔴" if p["stock_actual"] <= 0 else "🟡"
                    st.write(f"{color} **{p['codigo']}** — {p['stock_actual']} uds")
            else:
                st.success("✅ Todo en orden")
        else:
            st.info("Sin productos.")

# ══════════════════════════════════════════════════════════════════════════════
# INVENTARIO
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "📦 Inventario":
    st.title("📦 Inventario")

    tab1, tab2, tab3 = st.tabs(["📋 Ver inventario", "➕ Agregar / Editar producto", "🔍 Trazabilidad"])

    with tab1:
        df = get_productos()
        if df.empty:
            st.info("Sin productos. Ve a 'Agregar producto' para empezar.")
        else:
            col1, col2 = st.columns([2,1])
            buscar = col1.text_input("🔍 Buscar", placeholder="Código o descripción...")
            cat_opts = ["Todas"] + sorted(df["categoria"].unique().tolist())
            cat_fil  = col2.selectbox("Categoría", cat_opts)

            fil = df.copy()
            if buscar:
                fil = fil[fil["codigo"].str.contains(buscar, case=False, na=False) |
                          fil["descripcion"].str.contains(buscar, case=False, na=False)]
            if cat_fil != "Todas":
                fil = fil[fil["categoria"] == cat_fil]

            fil["margen"] = fil.apply(
                lambda r: f"{((r['precio_venta']-r['precio_costo'])/r['precio_costo']*100):.0f}%"
                if r["precio_costo"] > 0 else "—", axis=1)
            fil["stock_status"] = fil.apply(
                lambda r: "🔴 Agotado" if r["stock_actual"]<=0
                else ("🟡 Bajo" if r["stock_actual"]<=r["stock_minimo"] else "🟢 OK"), axis=1)

            st.dataframe(
                fil[["codigo","descripcion","categoria","stock_actual","stock_minimo",
                     "precio_costo","precio_venta","margen","stock_status","unidad"]].rename(columns={
                    "codigo":"Código","descripcion":"Descripción","categoria":"Categoría",
                    "stock_actual":"Stock","stock_minimo":"Mín.","precio_costo":"Costo $",
                    "precio_venta":"Venta $","margen":"Margen","stock_status":"Estado","unidad":"Unidad"}),
                use_container_width=True, hide_index=True)

            # Valor total del inventario filtrado
            fil["valor_stock"] = fil["stock_actual"] * fil["precio_costo"]
            valor_total_fil = fil["valor_stock"].sum()
            valor_venta_fil = (fil["stock_actual"] * fil["precio_venta"]).sum()
            vi1, vi2 = st.columns(2)
            vi1.metric("💰 Valor al costo (inventario filtrado)", fmt_usd(valor_total_fil),
                       help="Stock actual × precio costo")
            vi2.metric("🏷️ Valor al precio de venta", fmt_usd(valor_venta_fil),
                       help="Stock actual × precio de venta")

            st.divider()
            csv = fil.drop(columns=["valor_stock"], errors="ignore").to_csv(index=False).encode("utf-8")
            st.download_button("📥 Descargar CSV", csv, "inventario.csv", "text/csv")

    with tab2:
        df = get_productos()
        modo = st.radio("Modo", ["Agregar nuevo", "Editar existente"], horizontal=True)
        prod_sel = None

        if modo == "Editar existente" and not df.empty:
            opciones = {f"{r['codigo']} — {r['descripcion']}": r for _, r in df.iterrows()}
            sel = st.selectbox("Selecciona producto", list(opciones.keys()))
            prod_sel = opciones[sel]

        with st.form("form_producto"):
            c1, c2 = st.columns(2)
            codigo = c1.text_input("Código *", value=prod_sel["codigo"] if prod_sel is not None else "")
            cat    = c2.selectbox("Categoría", ["Bisagra","Clip","Manilla","Pomo","Policarbonato","Kit","Otro"],
                                  index=["Bisagra","Clip","Manilla","Pomo","Policarbonato","Kit","Otro"].index(
                                      prod_sel["categoria"]) if prod_sel is not None else 0)
            desc   = st.text_input("Descripción *", value=prod_sel["descripcion"] if prod_sel is not None else "")
            c3, c4, c5 = st.columns(3)
            stock  = c3.number_input("Stock actual", min_value=0, value=int(prod_sel["stock_actual"]) if prod_sel is not None else 0)
            stock_min = c4.number_input("Stock mínimo", min_value=0, value=int(prod_sel["stock_minimo"]) if prod_sel is not None else 2)
            unidad = c5.selectbox("Unidad", ["Unidad","Par","Caja","Metro","Kit"],
                                  index=["Unidad","Par","Caja","Metro","Kit"].index(
                                      prod_sel["unidad"]) if prod_sel is not None and prod_sel["unidad"] in ["Unidad","Par","Caja","Metro","Kit"] else 0)
            c6, c7 = st.columns(2)
            costo  = c6.number_input("Precio costo ($)", min_value=0.0, step=0.01,
                                     value=float(prod_sel["precio_costo"]) if prod_sel is not None else 0.0)
            pventa = c7.number_input("Precio venta ($)", min_value=0.0, step=0.01,
                                     value=float(prod_sel["precio_venta"]) if prod_sel is not None else 0.0)

            if costo > 0 and pventa > 0:
                margen = (pventa - costo) / costo * 100
                profit_u = pventa - costo
                st.info(f"📊 Margen: **{margen:.1f}%** — Profit por unidad: **{fmt_usd(profit_u)}**")

            guardar = st.form_submit_button("💾 Guardar producto", use_container_width=True, type="primary")

        if guardar:
            if not codigo or not desc:
                error("Código y descripción son obligatorios")
            else:
                codigo_norm = codigo.upper().strip()
                data = {"codigo": codigo_norm, "descripcion": desc, "categoria": cat,
                        "stock_actual": stock, "stock_minimo": stock_min,
                        "precio_costo": costo, "precio_venta": pventa, "unidad": unidad}
                if modo == "Editar existente" and prod_sel is not None:
                    # Si cambió el código, verificar que el nuevo no choque con otro producto
                    if codigo_norm != prod_sel["codigo"]:
                        dup = sb.table("dim_productos").select("id").eq("codigo", codigo_norm).execute()
                        if dup.data:
                            error(f"Ya existe otro producto con el código '{codigo_norm}'")
                            st.stop()
                    try:
                        sb.table("dim_productos").update(data).eq("id", prod_sel["id"]).execute()
                        success("Producto actualizado")
                        st.rerun()
                    except Exception as e:
                        error(f"No se pudo actualizar el producto: {str(e)[:120]}")
                else:
                    # Validar código duplicado ANTES de intentar insertar
                    dup = sb.table("dim_productos").select("id, descripcion").eq("codigo", codigo_norm).execute()
                    if dup.data:
                        existente = dup.data[0].get("descripcion", "")
                        error(f"Ya existe un producto con el código '{codigo_norm}' ({existente}). Usa un código distinto o edítalo desde 'Editar existente'.")
                    else:
                        data["id"] = str(uuid.uuid4())
                        try:
                            # Guardar stock inicial para auditoría de trazabilidad
                            sb.table("dim_productos").insert({**data, "stock_inicial": stock}).execute()
                            success("Producto agregado")
                            st.rerun()
                        except Exception as e:
                            msg = str(e)
                            if "stock_inicial" in msg or "column" in msg.lower():
                                # La columna stock_inicial no existe aún — insertar sin ella
                                try:
                                    sb.table("dim_productos").insert(data).execute()
                                    success("Producto agregado (sin stock inicial — ejecuta la migración SQL para activar auditoría)")
                                    st.rerun()
                                except Exception as e2:
                                    error(f"No se pudo guardar el producto: {str(e2)[:120]}")
                            else:
                                error(f"No se pudo guardar el producto: {msg[:120]}")


    with tab3:
        st.subheader("🔍 Trazabilidad por producto")
        st.caption("Reconstruye la historia completa de un producto: stock inicial → pedidos → ventas → stock actual.")

        df_prods = get_productos()
        if df_prods.empty:
            st.info("Sin productos registrados.")
            st.stop()  # safe: only triggers if product table is completely empty

        prod_opts = {f"{r['codigo']} — {r['descripcion']}": r for _, r in df_prods.iterrows()}
        prod_sel_traz = st.selectbox("Selecciona producto", list(prod_opts.keys()), key="traz_prod")
        prod_traz = prod_opts[prod_sel_traz]
        prod_id   = str(prod_traz["id"])
        stock_db  = int(prod_traz["stock_actual"])

        st.divider()

        # Recolectar todos los movimientos del producto
        movimientos_hist = []

        # 1. Stock inicial (asumimos que el stock inicial fue lo que quedó registrado
        #    en la creación del producto — lo marcamos como referencia)
        movimientos_hist.append({
            "fecha": "—",
            "tipo": "📋 Stock inicial",
            "referencia": "Carga inicial del sistema",
            "cantidad": "—",
            "efecto": "—",
            "stock_resultado": "—",
            "_orden": 0,
            "_stock_calc": None
        })

        # 2. Pedidos que incluyen este producto
        try:
            ped_items_r = sb.table("fact_pedido_items")                .select("*, fact_pedidos(fecha, estado, proveedor_nombre)")                .eq("producto_id", prod_id).execute()
            for pi in (ped_items_r.data or []):
                ped = pi.get("fact_pedidos") or {}
                estado_p = ped.get("estado","")
                if estado_p == "Recibido":
                    tipo_label = "🚚 Pedido recibido"
                elif estado_p == "Cancelado":
                    tipo_label = "🚫 Pedido cancelado"
                else:
                    tipo_label = "🕐 Pedido pendiente"
                movimientos_hist.append({
                    "fecha": ped.get("fecha","—"),
                    "tipo": tipo_label,
                    "referencia": ped.get("proveedor_nombre","—"),
                    "cantidad": int(pi["cantidad"]),
                    "efecto": f'+{pi["cantidad"]}',
                    "costo_unit": float(pi.get("costo_unitario", 0)),
                    "estado_ped": estado_p,
                    "_orden": 1,
                    "_stock_calc": None
                })
        except Exception as e:
            st.warning(f"Error leyendo pedidos: {e}")

        # 3. Ventas que incluyen este producto
        try:
            vta_items_r = sb.table("fact_venta_items")                .select("*, fact_ventas(fecha, estado, dim_clientes(nombre))")                .eq("producto_id", prod_id).execute()
            for vi in (vta_items_r.data or []):
                vta = vi.get("fact_ventas") or {}
                cli = vta.get("dim_clientes")
                cli_nombre = cli["nombre"] if isinstance(cli, dict) else "Cliente directo"
                movimientos_hist.append({
                    "fecha": vta.get("fecha","—"),
                    "tipo": "🛒 Venta" if vta.get("estado") == "Completada" else f"🔸 Venta ({vta.get('estado','')})",
                    "referencia": cli_nombre,
                    "cantidad": int(vi["cantidad"]),
                    "efecto": f'-{vi["cantidad"]}',
                    "precio_unit": float(vi.get("precio_unitario", 0)),
                    "estado_vta": vta.get("estado",""),
                    "_orden": 2,
                    "_stock_calc": None
                })
        except Exception as e:
            st.warning(f"Error leyendo ventas: {e}")

        # Ordenar por fecha luego por tipo
        def sort_key(m):
            f = m["fecha"]
            return (f if f != "—" else "0000-00-00", m["_orden"])

        movimientos_hist.sort(key=sort_key)

        # Calcular entradas y salidas confirmadas
        entradas = sum(m["cantidad"] for m in movimientos_hist
                      if m["tipo"] == "🚚 Pedido recibido" and isinstance(m["cantidad"], int))
        salidas  = sum(m["cantidad"] for m in movimientos_hist
                      if "🛒 Venta" in m["tipo"] and m.get("estado_vta") == "Completada" and isinstance(m["cantidad"], int))

        # Stock inicial REAL guardado en la DB (auditoría verdadera).
        # Si el producto es anterior a esta función (sin stock_inicial), se
        # reconstruye hacia atrás y la auditoría es solo referencial.
        stock_ini_db = prod_traz.get("stock_inicial") if hasattr(prod_traz, "get") else prod_traz["stock_inicial"] if "stock_inicial" in prod_traz else None
        try:
            stock_ini_db = int(stock_ini_db) if stock_ini_db is not None and not pd.isna(stock_ini_db) else None
        except (TypeError, ValueError):
            stock_ini_db = None

        auditoria_real = stock_ini_db is not None
        if auditoria_real:
            stock_inicial_calc = stock_ini_db
        else:
            stock_inicial_calc = stock_db - entradas + salidas  # referencial (no audita)
            st.info("ℹ️ Este producto no tiene stock inicial registrado — la comparación es solo referencial. Los productos nuevos guardan su stock inicial automáticamente.")

        rows_traz = []
        rows_traz.append({
            "Fecha":       "Inicio",
            "Tipo":        "📋 Stock inicial",
            "Referencia":  "Registrado en el sistema" if auditoria_real else "Reconstruido (referencial)",
            "Movimiento":  "—",
            "Stock calc.": stock_inicial_calc
        })

        stock_running = stock_inicial_calc
        for m in movimientos_hist:
            if m["tipo"] == "📋 Stock inicial":
                continue
            es_entrada = "Pedido recibido" in m["tipo"]
            es_venta_comp = "🛒 Venta" in m["tipo"] and m.get("estado_vta") == "Completada"

            if es_entrada:
                stock_running += m["cantidad"]
            elif es_venta_comp:
                stock_running -= m["cantidad"]

            extra = ""
            if "costo_unit" in m:
                extra = f"Costo: ${m['costo_unit']:.2f}/u"
            elif "precio_unit" in m:
                extra = f"P.Venta: ${m['precio_unit']:.2f}/u"

            # Determinar etiqueta del movimiento según estado
            if es_entrada or es_venta_comp:
                mov_label = m["efecto"]
            elif "cancelado" in m["tipo"].lower():
                mov_label = "anulado"
            elif "pendiente" in m["tipo"].lower():
                mov_label = f"{m['efecto']} (al recibir)"
            else:
                mov_label = f"{m['efecto']} (sin efecto)"

            rows_traz.append({
                "Fecha":       m["fecha"],
                "Tipo":        m["tipo"],
                "Referencia":  m["referencia"] + (f" · {extra}" if extra else ""),
                "Movimiento":  mov_label,
                "Stock calc.": stock_running if (es_entrada or es_venta_comp) else "—"
            })

        st.dataframe(pd.DataFrame(rows_traz), use_container_width=True, hide_index=True)

        # Comparación final
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("Stock calculado", stock_running)
        c2.metric("Stock en base de datos", stock_db)
        diferencia = stock_running - stock_db
        if diferencia == 0:
            c3.metric("Diferencia", "0 ✅")
            if auditoria_real:
                st.success("✅ Auditoría OK: el historial de movimientos reproduce exactamente el stock actual.")
            else:
                st.success("✅ El historial reconstruido coincide con el stock actual (comparación referencial).")
        else:
            c3.metric("Diferencia", f"{diferencia:+d} ⚠️")
            st.warning(f"⚠️ Diferencia de **{abs(diferencia)} unidades** entre el historial y la base de datos. Causas posibles: ajuste manual de stock en 'Editar producto', un registro faltante, o un error de captura. Revisa los movimientos listados arriba contra tus documentos físicos.")

        # Resumen del producto
        st.divider()
        col_a, col_b = st.columns(2)
        col_a.markdown(f"""
**Código:** {prod_traz['codigo']}  
**Descripción:** {prod_traz['descripcion']}  
**Categoría:** {prod_traz['categoria']}  
**Unidad:** {prod_traz['unidad']}
        """)
        col_b.markdown(f"""
**Precio costo:** ${prod_traz['precio_costo']:.2f}  
**Precio venta:** ${prod_traz['precio_venta']:.2f}  
**Margen:** { ((prod_traz['precio_venta']-prod_traz['precio_costo'])/prod_traz['precio_costo']*100) if prod_traz['precio_costo']>0 else 0 :.1f}% sobre costo  
**Stock mínimo:** {prod_traz['stock_minimo']} uds
        """)

# ══════════════════════════════════════════════════════════════════════════════
# NUEVA VENTA
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "🛒 Nueva Venta":
    st.title("🛒 Nueva Venta")

    # Confirmación persistente de la última venta registrada
    if st.session_state.get("ultima_venta_ok"):
        info_v = st.session_state["ultima_venta_ok"]
        st.success(f"✅ Venta registrada — Ref: **{info_v['ref']}** · Cliente: {info_v['cliente']} · "
                   f"Total: {info_v['total']} · Estado: {info_v['estado']}. "
                   f"Puedes verla en 'Historial Ventas'.")
        if st.button("Registrar otra venta", key="clear_venta_ok"):
            del st.session_state["ultima_venta_ok"]
            st.rerun()

    productos_df = get_productos()
    clientes_df  = get_clientes()

    if productos_df.empty:
        st.warning("⚠️ No hay productos en inventario. Agrega productos primero.")
        st.stop()

    if "items_venta" not in st.session_state:
        st.session_state.items_venta = []

    col1, col2 = st.columns(2)
    with col1:
        clientes_opts = ["— Sin cliente —"] + clientes_df["nombre"].tolist() if not clientes_df.empty else ["— Sin cliente —"]
        cliente_sel = st.selectbox("👤 Cliente", clientes_opts)
    with col2:
        fecha_venta = st.date_input("📅 Fecha", value=date.today())

    col3, col4 = st.columns(2)
    with col3:
        estado_venta = st.selectbox("Estado", ["Completada","Pendiente de pago","Cancelada"])
    with col4:
        notas_venta = st.text_input("Notas (opcional)")

    st.divider()
    st.subheader("➕ Agregar productos")

    prods_opts = {f"{r['codigo']} — {r['descripcion']} (Stock: {r['stock_actual']})": r
                  for _, r in productos_df.iterrows()}
    pc1, pc2, pc3 = st.columns([3,1,1])
    prod_elegido = pc1.selectbox("Producto", list(prods_opts.keys()), label_visibility="collapsed")
    prod_data = prods_opts[prod_elegido]
    cantidad  = pc2.number_input("Cant.", min_value=1,
                                  max_value=int(prod_data["stock_actual"]) if prod_data["stock_actual"] > 0 else 999,
                                  value=1)
    precio_u  = pc3.number_input("Precio $", min_value=0.0, step=0.01,
                                  value=float(prod_data["precio_venta"]))

    # Mostrar profit del producto seleccionado en tiempo real
    costo_sel = float(prod_data["precio_costo"])
    if precio_u > 0 and costo_sel > 0:
        profit_u_sel = precio_u - costo_sel
        margen_sel   = profit_u_sel / costo_sel * 100 if costo_sel > 0 else 0
        col_p1, col_p2, col_p3 = st.columns(3)
        col_p1.caption(f"Costo: **{fmt_usd(costo_sel)}**")
        col_p2.caption(f"Profit u.: **{fmt_usd(profit_u_sel)}**")
        col_p3.caption(f"Margen: **{margen_sel:.1f}%**")

    if st.button("➕ Agregar a la venta", use_container_width=True):
        existing = next((i for i in st.session_state.items_venta if i["producto_id"] == prod_data["id"]), None)
        if existing:
            existing["cantidad"] += cantidad
            existing["subtotal"] = existing["cantidad"] * existing["precio_unitario"]
        else:
            st.session_state.items_venta.append({
                "producto_id": str(prod_data["id"]),
                "codigo": prod_data["codigo"],
                "descripcion": prod_data["descripcion"],
                "cantidad": cantidad,
                "precio_unitario": precio_u,
                "costo_unitario": costo_sel,
                "subtotal": cantidad * precio_u
            })
        st.rerun()

    # Tabla de items con profit y edición por fila
    if st.session_state.items_venta:
        st.divider()
        st.subheader("🧾 Productos en esta venta")

        total_ingresos = 0
        total_costo    = 0

        for idx, it in enumerate(st.session_state.items_venta):
            subtotal = it["subtotal"]
            costo_t  = it["costo_unitario"] * it["cantidad"]
            profit_t = subtotal - costo_t
            margen_t = (profit_t / costo_t * 100) if costo_t > 0 else 0
            total_ingresos += subtotal
            total_costo    += costo_t

            with st.container():
                col_desc, col_qty, col_price, col_profit, col_margin, col_del = st.columns([3,1,1,1,1,0.5])
                col_desc.markdown(f"**{it['codigo']}** {it['descripcion']}")

                item_key = it["producto_id"]
                new_qty = col_qty.number_input(
                    "Cant.", min_value=1, value=it["cantidad"],
                    key=f"qty_{item_key}", label_visibility="collapsed")
                new_price = col_price.number_input(
                    "Precio", min_value=0.0, step=0.01, value=it["precio_unitario"],
                    key=f"price_{item_key}", label_visibility="collapsed", format="%.2f")

                # Actualizar si cambió cantidad o precio
                if new_qty != it["cantidad"] or new_price != it["precio_unitario"]:
                    st.session_state.items_venta[idx]["cantidad"] = new_qty
                    st.session_state.items_venta[idx]["precio_unitario"] = new_price
                    st.session_state.items_venta[idx]["subtotal"] = new_qty * new_price
                    st.rerun()

                nuevo_subtotal = new_qty * new_price
                nuevo_costo_t  = it["costo_unitario"] * new_qty
                nuevo_profit   = nuevo_subtotal - nuevo_costo_t
                nuevo_margen   = (nuevo_profit / nuevo_costo_t * 100) if nuevo_costo_t > 0 else 0
                col_profit.caption(f"Profit: **{fmt_usd(nuevo_profit)}**")
                col_margin.caption(f"**{nuevo_margen:.1f}%**")

                if col_del.button("✕", key=f"del_{item_key}", help="Eliminar este producto"):
                    st.session_state.items_venta.pop(idx)
                    # Limpiar estado de widgets del item eliminado para evitar herencia de valores
                    for k in (f"qty_{item_key}", f"price_{item_key}"):
                        if k in st.session_state:
                            del st.session_state[k]
                    st.rerun()

        # Recalcular totales con valores actuales
        total_ingresos = sum(i["subtotal"] for i in st.session_state.items_venta)
        total_costo    = sum(i["costo_unitario"] * i["cantidad"] for i in st.session_state.items_venta)
        total_profit = total_ingresos - total_costo
        margen_total = (total_profit / total_costo * 100) if total_costo > 0 else 0

        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("💵 Total venta", fmt_usd(total_ingresos))
        m2.metric("📦 Costo total", fmt_usd(total_costo))
        m3.metric("💚 Profit bruto", fmt_usd(total_profit))
        m4.metric("📊 Margen", f"{margen_total:.1f}%")

        st.divider()
        rc1, rc2 = st.columns(2)
        if rc1.button("🗑️ Limpiar venta", use_container_width=True):
            st.session_state.items_venta = []
            st.rerun()

        if rc2.button("✅ Registrar venta", use_container_width=True, type="primary"):
            try:
                ensure_fecha(fecha_venta)
                cliente_id = None
                if cliente_sel != "— Sin cliente —" and not clientes_df.empty:
                    match = clientes_df[clientes_df["nombre"] == cliente_sel]
                    if not match.empty:
                        cliente_id = match.iloc[0]["id"]

                venta_id = str(uuid.uuid4())
                sb.table("fact_ventas").insert({
                    "id": venta_id, "cliente_id": cliente_id,
                    "fecha": str(fecha_venta), "estado": estado_venta,
                    "total": total_ingresos, "notas": notas_venta
                }).execute()

                for item in st.session_state.items_venta:
                    sb.table("fact_venta_items").insert({
                        "id": str(uuid.uuid4()), "venta_id": venta_id,
                        "producto_id": item["producto_id"],
                        "cantidad": item["cantidad"],
                        "precio_unitario": item["precio_unitario"],
                        "subtotal": item["subtotal"]
                    }).execute()
                    if estado_venta == "Completada":
                        prod_real = sb.table("dim_productos").select("stock_actual").eq("id", item["producto_id"]).execute()
                        stock_real = prod_real.data[0]["stock_actual"] if prod_real.data else 0
                        sb.table("dim_productos").update({
                            "stock_actual": stock_real - item["cantidad"]
                        }).eq("id", item["producto_id"]).execute()

                if estado_venta == "Completada":
                    registrar_movimiento("ingreso","Venta", total_ingresos, fecha_venta,
                                        f"Venta {venta_id[:8]} — {cliente_sel}", venta_id)

                st.session_state["ultima_venta_ok"] = {
                    "ref": venta_id[:8].upper(),
                    "cliente": cliente_sel if cliente_sel != "— Sin cliente —" else "Cliente directo",
                    "total": fmt_usd(total_ingresos),
                    "estado": estado_venta,
                }
                st.session_state.items_venta = []
                st.rerun()
            except Exception as e:
                error(f"No se pudo registrar la venta: {str(e)[:120]}")
    else:
        st.info("Agrega productos arriba para comenzar la venta.")


# ══════════════════════════════════════════════════════════════════════════════
# HISTORIAL VENTAS
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "📋 Historial Ventas":
    st.title("📋 Historial de Ventas")

    ventas_df = get_ventas()
    if ventas_df.empty:
        st.info("Sin ventas registradas.")
        st.stop()

    ventas_df["cliente_nombre"] = ventas_df["dim_clientes"].apply(
        lambda x: x["nombre"] if isinstance(x, dict) else "Cliente directo")

    c1, c2, c3 = st.columns(3)
    estado_fil = c1.selectbox("Estado", ["Todos","Completada","Pendiente de pago","Cancelada"])
    fecha_desde = c2.date_input("Desde", value=date(date.today().year, 1, 1))
    fecha_hasta = c3.date_input("Hasta", value=date.today())

    fil = ventas_df.copy()
    fil["fecha"] = pd.to_datetime(fil["fecha"]).dt.date
    fil = fil[(fil["fecha"] >= fecha_desde) & (fil["fecha"] <= fecha_hasta)]
    if estado_fil != "Todos":
        fil = fil[fil["estado"] == estado_fil]

    total_periodo = fil["total"].sum()
    st.metric("Total período", fmt_usd(total_periodo))

    fil_display = fil[["fecha","cliente_nombre","total","estado"]].copy()
    fil_display.columns = ["Fecha","Cliente","Total","Estado"]
    fil_display["Total"] = fil_display["Total"].apply(fmt_usd)
    st.dataframe(fil_display, use_container_width=True, hide_index=True)

    # ── Ventas pendientes de pago ──────────────────────────────────────────────
    pendientes = ventas_df[ventas_df["estado"] == "Pendiente de pago"]
    if not pendientes.empty:
        st.divider()
        st.subheader(f"⏳ Ventas pendientes de cobro ({len(pendientes)})")
        st.caption("Aquí puedes confirmar el cobro o cancelar ventas que no se concretaron.")

        pend_opts = {
            f"{r['fecha']} — {r['cliente_nombre']} — {fmt_usd(r['total'])}": r
            for _, r in pendientes.iterrows()
        }
        pend_sel_key = st.selectbox("Selecciona venta pendiente", list(pend_opts.keys()), key="pend_sel")
        pend_venta = pend_opts[pend_sel_key]

        # Mostrar items de la venta pendiente
        items_pend = get_venta_items(pend_venta["id"])
        if not items_pend.empty:
            items_pend["Producto"] = items_pend["dim_productos"].apply(
                lambda x: f"{x['codigo']} — {x['descripcion']}" if isinstance(x, dict) else "—")
            items_pend["P. Venta"] = items_pend["precio_unitario"].apply(fmt_usd)
            items_pend["Subtotal"] = items_pend["subtotal"].apply(fmt_usd)
            st.dataframe(
                items_pend[["Producto","cantidad","P. Venta","Subtotal"]].rename(
                    columns={"cantidad":"Cant."}),
                use_container_width=True, hide_index=True)
            st.markdown(f"**Total: {fmt_usd(pend_venta['total'])}**")

        # Advertencia de stock antes de confirmar
        alertas_stock = []
        if not items_pend.empty:
            for _, it in items_pend.iterrows():
                prod_r = sb.table("dim_productos").select("codigo, stock_actual").eq(
                    "id", it["producto_id"]).execute()
                if prod_r.data:
                    p = prod_r.data[0]
                    if p["stock_actual"] < it["cantidad"]:
                        alertas_stock.append(
                            f"⚠️ **{p['codigo']}**: stock disponible ({p['stock_actual']}) "
                            f"menor a cantidad vendida ({it['cantidad']})")
        if alertas_stock:
            for alerta in alertas_stock:
                st.warning(alerta)

        col_comp, col_canc = st.columns(2)
        btn_completar = col_comp.button(
            "✅ Confirmar cobro — marcar como Completada",
            use_container_width=True, type="primary", key="btn_completar_pend")
        btn_cancelar = col_canc.button(
            "❌ Cancelar esta venta",
            use_container_width=True, key="btn_cancelar_pend")

        if btn_completar:
            try:
                # Cambiar estado
                sb.table("fact_ventas").update({"estado": "Completada"}).eq(
                    "id", pend_venta["id"]).execute()
                # Descontar stock en tiempo real por cada item
                items_raw = get_venta_items(pend_venta["id"])
                for _, item in items_raw.iterrows():
                    prod_real = sb.table("dim_productos").select("stock_actual").eq(
                        "id", item["producto_id"]).execute()
                    stock_real = prod_real.data[0]["stock_actual"] if prod_real.data else 0
                    nuevo_stock = max(0, stock_real - item["cantidad"])
                    sb.table("dim_productos").update({"stock_actual": nuevo_stock}).eq(
                        "id", item["producto_id"]).execute()
                # Registrar ingreso
                registrar_movimiento(
                    "ingreso", "Venta", pend_venta["total"],
                    pend_venta["fecha"],
                    f"Cobro venta {pend_venta['id'][:8]} — {pend_venta['cliente_nombre']}",
                    pend_venta["id"])
                success(f"Venta confirmada — stock actualizado e ingreso registrado")
                st.rerun()
            except Exception as e:
                error(f"Error al confirmar: {e}")

        if btn_cancelar:
            try:
                sb.table("fact_ventas").update({"estado": "Cancelada"}).eq(
                    "id", pend_venta["id"]).execute()
                success("Venta cancelada — el stock no fue afectado")
                st.rerun()
            except Exception as e:
                error(f"Error al cancelar: {e}")

    st.divider()
    st.subheader("🔍 Ver detalle con profit")
    if not fil.empty:
        venta_opts = {f"{r['fecha']} — {r['cliente_nombre']} — {fmt_usd(r['total'])} [{r['estado']}]": r["id"]
                      for _, r in fil.iterrows()}
        venta_sel = st.selectbox("Selecciona venta", list(venta_opts.keys()))
        items = get_venta_items(venta_opts[venta_sel])
        if not items.empty:
            items["producto"] = items["dim_productos"].apply(
                lambda x: f"{x['codigo']} — {x['descripcion']}" if isinstance(x, dict) else "—")
            items = calcular_profit_items(items)
            items["Precio u."] = items["precio_unitario"].apply(fmt_usd)
            items["Costo u."]  = items["costo_unit"].apply(fmt_usd)
            items["Subtotal"]  = items["subtotal"].apply(fmt_usd)
            items["Profit"]    = items["profit"].apply(fmt_usd)
            items["Margen %"]  = items["margen_pct"].apply(lambda x: f"{x:.1f}%")
            st.dataframe(
                items[["producto","cantidad","Precio u.","Costo u.","Subtotal","Profit","Margen %"]].rename(
                    columns={"producto":"Producto","cantidad":"Cant."}),
                use_container_width=True, hide_index=True)

    # ── EDITAR UNA VENTA EXISTENTE ─────────────────────────────────────────────
    st.divider()
    with st.expander("✏️ Editar una venta registrada"):
        st.caption("Corrige productos, cantidades o precios de una venta ya registrada. "
                   "El stock y el ingreso en Finanzas se ajustan automáticamente.")

        # Solo Completadas y Pendientes de pago son editables
        editables = ventas_df[ventas_df["estado"].isin(["Completada","Pendiente de pago"])].copy()
        if editables.empty:
            st.info("No hay ventas editables.")
        else:
            ed_opts = {
                f"{r['fecha']} — {r['cliente_nombre']} — {fmt_usd(r['total'])} [{r['estado']}]": r["id"]
                for _, r in editables.iterrows()
            }
            ed_sel_key = st.selectbox("Selecciona la venta a editar", list(ed_opts.keys()), key="edit_venta_sel")
            edit_venta_id = ed_opts[ed_sel_key]
            venta_row = editables[editables["id"] == edit_venta_id].iloc[0]
            estado_original = venta_row["estado"]

            # Cargar items actuales a session_state (una sola vez por venta seleccionada)
            sskey = f"edit_items_{edit_venta_id}"
            if sskey not in st.session_state:
                items_orig = get_venta_items(edit_venta_id)
                cargados = []
                if not items_orig.empty:
                    for _, it in items_orig.iterrows():
                        prod = it.get("dim_productos") or {}
                        cargados.append({
                            "producto_id": str(it["producto_id"]),
                            "codigo": prod.get("codigo","?") if isinstance(prod, dict) else "?",
                            "descripcion": prod.get("descripcion","?") if isinstance(prod, dict) else "?",
                            "cantidad": int(it["cantidad"]),
                            "precio_unitario": float(it["precio_unitario"]),
                            "costo_unitario": float(prod.get("precio_costo",0)) if isinstance(prod, dict) else 0.0,
                            "subtotal": float(it["subtotal"]),
                        })
                st.session_state[sskey] = cargados

            edit_items = st.session_state[sskey]

            # Agregar un producto nuevo a la venta editada
            prods_all = get_productos()
            st.markdown("**Agregar producto a esta venta**")
            ap1, ap2, ap3, ap4 = st.columns([3,1,1,1])
            prod_add_opts = {f"{r['codigo']} — {r['descripcion']}": r for _, r in prods_all.iterrows()}
            prod_add_sel = ap1.selectbox("Producto", list(prod_add_opts.keys()),
                                          key=f"add_prod_{edit_venta_id}", label_visibility="collapsed")
            prod_add = prod_add_opts[prod_add_sel]
            qty_add = ap2.number_input("Cant.", min_value=1, value=1,
                                        key=f"add_qty_{edit_venta_id}", label_visibility="collapsed")
            price_add = ap3.number_input("Precio", min_value=0.0, step=0.01,
                                          value=float(prod_add["precio_venta"]),
                                          key=f"add_price_{edit_venta_id}", label_visibility="collapsed", format="%.2f")
            if ap4.button("➕ Añadir", key=f"add_btn_{edit_venta_id}"):
                existing = next((x for x in edit_items if x["producto_id"] == str(prod_add["id"])), None)
                if existing:
                    existing["cantidad"] += qty_add
                    existing["subtotal"] = existing["cantidad"] * existing["precio_unitario"]
                else:
                    edit_items.append({
                        "producto_id": str(prod_add["id"]),
                        "codigo": prod_add["codigo"],
                        "descripcion": prod_add["descripcion"],
                        "cantidad": qty_add,
                        "precio_unitario": price_add,
                        "costo_unitario": float(prod_add["precio_costo"]),
                        "subtotal": qty_add * price_add,
                    })
                st.rerun()

            # Listar items editables
            if not edit_items:
                st.info("Esta venta no tiene productos. Añade al menos uno o elimina la venta desde otra opción.")
            else:
                st.markdown("**Productos en la venta**")
                total_edit = 0
                for i, it in enumerate(edit_items):
                    k = it["producto_id"]
                    c_desc, c_qty, c_price, c_sub, c_del = st.columns([3,1,1,1,0.5])
                    c_desc.markdown(f"**{it['codigo']}** {it['descripcion']}")
                    nq = c_qty.number_input("Cant.", min_value=1, value=it["cantidad"],
                                             key=f"eq_{edit_venta_id}_{k}", label_visibility="collapsed")
                    npr = c_price.number_input("Precio", min_value=0.0, step=0.01, value=it["precio_unitario"],
                                                key=f"ep_{edit_venta_id}_{k}", label_visibility="collapsed", format="%.2f")
                    if nq != it["cantidad"] or npr != it["precio_unitario"]:
                        it["cantidad"] = nq
                        it["precio_unitario"] = npr
                        it["subtotal"] = nq * npr
                        st.rerun()
                    c_sub.markdown(fmt_usd(it["subtotal"]))
                    if c_del.button("✕", key=f"ed_del_{edit_venta_id}_{k}", help="Quitar producto"):
                        edit_items.pop(i)
                        st.rerun()
                    total_edit += it["subtotal"]

                st.markdown(f"### Nuevo total: **{fmt_usd(total_edit)}**")
                if estado_original != venta_row["estado"]:
                    pass

                colg1, colg2 = st.columns(2)
                guardar_edit = colg1.button("💾 Guardar cambios", type="primary",
                                             use_container_width=True, key=f"save_edit_{edit_venta_id}")
                cancelar_edit = colg2.button("↩️ Descartar cambios",
                                              use_container_width=True, key=f"discard_edit_{edit_venta_id}")

                if cancelar_edit:
                    del st.session_state[sskey]
                    st.rerun()

                # Advertencia de stock negativo antes de guardar (no bloquea)
                if estado_original == "Completada":
                    items_orig_check = get_venta_items(edit_venta_id)
                    orig_qty = {str(r["producto_id"]): int(r["cantidad"]) for _, r in items_orig_check.iterrows()} if not items_orig_check.empty else {}
                    avisos_neg = []
                    for x in edit_items:
                        pid = x["producto_id"]
                        pr = prods_all[prods_all["id"] == pid]
                        if not pr.empty:
                            stock_disp = int(pr.iloc[0]["stock_actual"]) + orig_qty.get(pid, 0)
                            if x["cantidad"] > stock_disp:
                                avisos_neg.append(f"**{x['codigo']}**: necesitas {x['cantidad']} pero solo hay {stock_disp} disponibles")
                    if avisos_neg:
                        st.warning("⚠️ Esta edición dejaría stock negativo en: " + "; ".join(avisos_neg) +
                                   ". Puedes continuar si es una venta contra pedido.")

                if guardar_edit:
                    if not edit_items:
                        error("La venta debe tener al menos un producto")
                    else:
                        try:
                            # ── PASO 1: Revertir efectos de la venta original ──────────
                            items_actuales = get_venta_items(edit_venta_id)
                            if estado_original == "Completada":
                                # Devolver al stock lo que la venta original había descontado
                                for _, it in items_actuales.iterrows():
                                    pr = sb.table("dim_productos").select("stock_actual").eq(
                                        "id", it["producto_id"]).execute()
                                    if pr.data:
                                        sb.table("dim_productos").update({
                                            "stock_actual": pr.data[0]["stock_actual"] + int(it["cantidad"])
                                        }).eq("id", it["producto_id"]).execute()

                            # ── PASO 2: Borrar los items viejos ────────────────────────
                            sb.table("fact_venta_items").delete().eq("venta_id", edit_venta_id).execute()

                            # ── PASO 3: Insertar los items nuevos ──────────────────────
                            nuevo_total = sum(x["subtotal"] for x in edit_items)
                            for x in edit_items:
                                sb.table("fact_venta_items").insert({
                                    "id": str(uuid.uuid4()), "venta_id": edit_venta_id,
                                    "producto_id": x["producto_id"],
                                    "cantidad": x["cantidad"],
                                    "precio_unitario": x["precio_unitario"],
                                    "subtotal": x["subtotal"]
                                }).execute()

                            # ── PASO 4: Aplicar el nuevo descuento de stock ────────────
                            if estado_original == "Completada":
                                for x in edit_items:
                                    pr = sb.table("dim_productos").select("stock_actual").eq(
                                        "id", x["producto_id"]).execute()
                                    if pr.data:
                                        sb.table("dim_productos").update({
                                            "stock_actual": pr.data[0]["stock_actual"] - x["cantidad"]
                                        }).eq("id", x["producto_id"]).execute()

                            # ── PASO 5: Actualizar el total de la venta ────────────────
                            sb.table("fact_ventas").update({"total": nuevo_total}).eq(
                                "id", edit_venta_id).execute()

                            # ── PASO 6: Corregir el ingreso en Finanzas (solo Completada) ─
                            if estado_original == "Completada":
                                mov = sb.table("fact_movimientos").select("id").eq(
                                    "referencia_id", edit_venta_id).eq("tipo","ingreso").execute()
                                if mov.data:
                                    sb.table("fact_movimientos").update({"monto": nuevo_total}).eq(
                                        "id", mov.data[0]["id"]).execute()

                            del st.session_state[sskey]
                            success("Venta actualizada — stock y finanzas ajustados")
                            st.rerun()
                        except Exception as e:
                            error(f"Error al actualizar la venta: {e}")

    st.divider()
    csv = fil.drop(columns=["dim_clientes"], errors="ignore").to_csv(index=False).encode("utf-8")
    st.download_button("📥 Exportar CSV", csv, "ventas.csv", "text/csv")

# ══════════════════════════════════════════════════════════════════════════════
# PEDIDOS
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "🚚 Pedidos":
    st.title("🚚 Pedidos a Proveedores")

    tab1, tab2 = st.tabs(["📋 Ver pedidos", "➕ Nuevo pedido"])

    with tab2:
        productos_df  = get_productos()
        proveedores_df = get_proveedores()

        if productos_df.empty:
            st.warning("No hay productos en inventario.")
            st.stop()

        c1, c2 = st.columns(2)
        provs = proveedores_df["nombre"].tolist() if not proveedores_df.empty else []
        prov_opts = provs + ["✏️ Escribir manualmente"]
        prov_sel  = c1.selectbox("Proveedor", prov_opts)
        if prov_sel == "✏️ Escribir manualmente":
            prov_nombre = c1.text_input("Nombre del proveedor")
        else:
            prov_nombre = prov_sel

        fecha_ped  = c2.date_input("Fecha del pedido", value=date.today())
        fecha_eta  = c2.date_input("Fecha estimada de llegada")

        st.divider()
        st.subheader("📦 Selecciona productos y cantidades")
        st.caption("Modifica solo los productos que necesitas — deja en 0 los que no vas a pedir.")

        ped_data = []
        for _, p in productos_df.iterrows():
            necesita = max(0, int(p["stock_minimo"]) - int(p["stock_actual"]))
            ped_data.append({
                "Código": p["codigo"],
                "Descripción": p["descripcion"],
                "Stock actual": int(p["stock_actual"]),
                "Stock mínimo": int(p["stock_minimo"]),
                "Sugerido": necesita,
                "Pedir": necesita,
                "Costo unit. $": float(p["precio_costo"]),
                "_id": p["id"]
            })

        ped_df = pd.DataFrame(ped_data)
        edited = st.data_editor(
            ped_df[["Código","Descripción","Stock actual","Stock mínimo","Sugerido","Pedir","Costo unit. $"]],
            use_container_width=True, hide_index=True,
            disabled=["Código","Descripción","Stock actual","Stock mínimo","Sugerido"],
            column_config={
                "Pedir": st.column_config.NumberColumn("Pedir", min_value=0, step=1),
                "Costo unit. $": st.column_config.NumberColumn("Costo unit. $", min_value=0.0, step=0.01, format="$%.2f"),
            }
        )

        items_pedido = edited[edited["Pedir"] > 0]
        if not items_pedido.empty:
            total_ped = (items_pedido["Pedir"] * items_pedido["Costo unit. $"]).sum()
            st.metric(f"Total estimado ({len(items_pedido)} productos)", fmt_usd(total_ped))

        # Mostrar confirmación persistente del último pedido registrado
        if st.session_state.get("ultimo_pedido_ok"):
            info_ped = st.session_state["ultimo_pedido_ok"]
            st.success(f"✅ Pedido registrado correctamente — Ref: **{info_ped['ref']}** · "
                       f"Proveedor: {info_ped['proveedor']} · Total: {info_ped['total']} · "
                       f"{info_ped['n_items']} producto(s). Ve a 'Ver pedidos' para gestionarlo.")
            if st.button("Entendido, registrar otro pedido", key="clear_ped_ok"):
                del st.session_state["ultimo_pedido_ok"]
                st.rerun()

        registrar_ped_btn = st.button("✅ Registrar pedido", type="primary", use_container_width=True,
                                       disabled=bool(st.session_state.get("registrando_pedido", False)))
        if registrar_ped_btn:
            if items_pedido.empty:
                warn("Agrega al menos un producto con cantidad > 0")
            elif not prov_nombre:
                warn("Ingresa el nombre del proveedor")
            else:
                # Bandera anti doble-registro
                st.session_state["registrando_pedido"] = True
                try:
                    ensure_fecha(fecha_ped)
                    pedido_id = str(uuid.uuid4())
                    total_ped = (items_pedido["Pedir"] * items_pedido["Costo unit. $"]).sum()
                    prov_id = None
                    if not proveedores_df.empty:
                        match = proveedores_df[proveedores_df["nombre"] == prov_nombre]
                        if not match.empty:
                            prov_id = match.iloc[0]["id"]

                    sb.table("fact_pedidos").insert({
                        "id": pedido_id, "proveedor_id": prov_id,
                        "proveedor_nombre": prov_nombre,
                        "fecha": str(fecha_ped), "fecha_eta": str(fecha_eta),
                        "estado": "Pendiente", "total": float(total_ped)
                    }).execute()

                    n_items = 0
                    for idx, row in items_pedido.iterrows():
                        prod_match = productos_df[productos_df["codigo"] == row["Código"]]
                        if prod_match.empty: continue
                        sb.table("fact_pedido_items").insert({
                            "id": str(uuid.uuid4()), "pedido_id": pedido_id,
                            "producto_id": prod_match.iloc[0]["id"],
                            "cantidad": int(row["Pedir"]),
                            "costo_unitario": float(row["Costo unit. $"]),
                            "subtotal": float(row["Pedir"] * row["Costo unit. $"])
                        }).execute()
                        n_items += 1

                    registrar_movimiento("egreso","Compra de mercancía", total_ped,
                                        fecha_ped, f"Pedido {pedido_id[:8]} — {prov_nombre}", pedido_id)

                    # Guardar confirmación persistente
                    st.session_state["ultimo_pedido_ok"] = {
                        "ref": pedido_id[:8].upper(),
                        "proveedor": prov_nombre,
                        "total": fmt_usd(total_ped),
                        "n_items": n_items,
                    }
                    st.session_state["registrando_pedido"] = False
                    st.rerun()
                except Exception as e:
                    st.session_state["registrando_pedido"] = False
                    error(f"No se pudo registrar el pedido: {str(e)[:120]}")

    with tab1:
        pedidos_df = get_pedidos()
        if pedidos_df.empty:
            st.info("Sin pedidos registrados.")
            st.stop()

        pedidos_df["proveedor"] = pedidos_df.apply(
            lambda r: r["dim_proveedores"]["nombre"] if isinstance(r.get("dim_proveedores"), dict)
            else r.get("proveedor_nombre","—"), axis=1)

        estado_fil_ped = st.selectbox("Filtrar por estado", ["Todos","Pendiente","Recibido","Cancelado"], key="fil_ped_estado")
        fil_ped = pedidos_df if estado_fil_ped == "Todos" else pedidos_df[pedidos_df["estado"] == estado_fil_ped]

        fil_ped_display = fil_ped[["id","fecha","proveedor","fecha_eta","total","estado"]].copy()
        fil_ped_display["Ref"] = fil_ped_display["id"].apply(lambda x: x[:8].upper())
        fil_ped_display = fil_ped_display[["Ref","fecha","proveedor","fecha_eta","total","estado"]]
        fil_ped_display.columns = ["Ref","Fecha","Proveedor","ETA","Total","Estado"]
        fil_ped_display["Total"] = fil_ped_display["Total"].apply(fmt_usd)
        st.dataframe(fil_ped_display, use_container_width=True, hide_index=True)

        csv_ped = fil_ped.drop(columns=["dim_proveedores"], errors="ignore").to_csv(index=False).encode("utf-8")
        st.download_button("📥 Exportar CSV", csv_ped, "pedidos.csv", "text/csv")

        st.divider()
        st.subheader("🔍 Ver detalle de pedido")
        if not fil_ped.empty:
            ped_opts_all = {f"[{r['id'][:8].upper()}] {r['fecha']} — {r['proveedor']} — {fmt_usd(r['total'])} [{r['estado']}]": r["id"]
                           for _, r in fil_ped.iterrows()}
            ped_det_sel = st.selectbox("Selecciona pedido", list(ped_opts_all.keys()), key="ped_det_sel")
            ped_det_id = ped_opts_all[ped_det_sel]

            items_det = get_pedido_items(ped_det_id)
            if not items_det.empty:
                items_det["Producto"] = items_det["dim_productos"].apply(
                    lambda x: f"{x['codigo']} — {x['descripcion']}" if isinstance(x, dict) else "—")
                items_det["Costo u."]  = items_det["costo_unitario"].apply(fmt_usd)
                items_det["Subtotal $"] = items_det["subtotal"].apply(fmt_usd)
                st.dataframe(
                    items_det[["Producto","cantidad","Costo u.","Subtotal $"]].rename(columns={"cantidad":"Cantidad"}),
                    use_container_width=True, hide_index=True)
                st.metric("Total del pedido", fmt_usd(items_det["subtotal"].sum()))

            ped_row = fil_ped[fil_ped["id"] == ped_det_id].iloc[0]
            if ped_row["estado"] == "Pendiente":
                st.divider()
                col_rec, col_can = st.columns(2)
                btn_recibir  = col_rec.button("✅ Marcar como recibido — actualiza stock",
                                               type="primary", use_container_width=True, key="btn_ped_recibir")
                btn_cancelar_ped = col_can.button("❌ Cancelar pedido",
                                                   use_container_width=True, key="btn_ped_cancelar")

                if btn_recibir:
                    try:
                        sb.table("fact_pedidos").update({"estado":"Recibido"}).eq("id", ped_det_id).execute()
                        items = get_pedido_items(ped_det_id)
                        for _, item in items.iterrows():
                            prod = sb.table("dim_productos").select("stock_actual").eq("id", item["producto_id"]).execute()
                            if prod.data:
                                nuevo_stock = prod.data[0]["stock_actual"] + item["cantidad"]
                                sb.table("dim_productos").update({"stock_actual": nuevo_stock}).eq("id", item["producto_id"]).execute()
                        success("Stock actualizado al recibir pedido")
                        st.rerun()
                    except Exception as e:
                        error(f"Error: {e}")

                if btn_cancelar_ped:
                    try:
                        sb.table("fact_pedidos").update({"estado":"Cancelado"}).eq("id", ped_det_id).execute()
                        # El egreso fue registrado al crear el pedido — se crea ingreso compensatorio
                        registrar_movimiento(
                            "ingreso", "Cancelación de pedido",
                            float(ped_row["total"]),
                            date.today(),
                            f"Reversión pedido cancelado {ped_det_id[:8]} — {ped_row['proveedor']}",
                            ped_det_id)
                        success("Pedido cancelado — egreso revertido en Finanzas")
                        st.rerun()
                    except Exception as e:
                        error(f"Error al cancelar: {e}")

            elif ped_row["estado"] == "Cancelado":
                st.warning("Este pedido fue cancelado. El egreso original fue revertido en Finanzas.")
            else:
                st.info(f"Este pedido ya está marcado como **{ped_row['estado']}**.")

# ══════════════════════════════════════════════════════════════════════════════
# CLIENTES
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "👥 Clientes":
    st.title("👥 Clientes")

    tab1, tab2, tab3_cli = st.tabs(["📋 Ver clientes", "➕ Agregar cliente", "✏️ Editar / Eliminar"])

    with tab1:
        df = get_clientes()
        if df.empty:
            st.info("Sin clientes registrados.")
        else:
            buscar = st.text_input("🔍 Buscar cliente")
            if buscar:
                df = df[df["nombre"].str.contains(buscar, case=False, na=False) |
                        df["rif_cedula"].str.contains(buscar, case=False, na=False)]

            ventas_df = get_ventas()
            resumen = []
            for _, c in df.iterrows():
                v = ventas_df[(ventas_df["dim_clientes"].apply(
                    lambda x: x.get("nombre") if isinstance(x, dict) else None) == c["nombre"]) &
                    (ventas_df["estado"] == "Completada")] if not ventas_df.empty else pd.DataFrame()
                resumen.append({
                    "Nombre": c["nombre"], "RIF/CI": c.get("rif_cedula",""),
                    "Teléfono": c.get("telefono",""), "Tipo": c.get("tipo",""),
                    "Compras": len(v), "Total $": fmt_usd(v["total"].sum()) if not v.empty else "$0.00"
                })
            st.dataframe(pd.DataFrame(resumen), use_container_width=True, hide_index=True)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Exportar CSV", csv, "clientes.csv", "text/csv")

    with tab2:
        with st.form("form_cliente"):
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre / Razón social *")
            rif    = c2.text_input("RIF / Cédula")
            c3, c4 = st.columns(2)
            tel    = c3.text_input("Teléfono")
            email  = c4.text_input("Email")
            dir_   = st.text_input("Dirección")
            tipo   = st.selectbox("Tipo", ["Persona natural","Empresa","Distribuidor"])
            guardar = st.form_submit_button("💾 Guardar cliente", use_container_width=True, type="primary")

        if guardar:
            if not nombre:
                error("El nombre es obligatorio")
            else:
                # Prevenir duplicados: verificar nombre existente (sin distinguir mayúsculas/espacios)
                existentes = sb.table("dim_clientes").select("id, nombre").execute()
                nombres_norm = {c["nombre"].strip().lower() for c in (existentes.data or [])}
                if nombre.strip().lower() in nombres_norm:
                    st.warning(f"⚠️ Ya existe un cliente llamado '{nombre.strip()}'. Verifica en 'Ver clientes' antes de crear un duplicado. Si realmente es otra persona con el mismo nombre, agrégale una distinción (ej: ciudad o apellido).")
                else:
                    sb.table("dim_clientes").insert({
                        "id": str(uuid.uuid4()), "nombre": nombre.strip(), "rif_cedula": rif,
                        "telefono": tel, "email": email, "direccion": dir_, "tipo": tipo
                    }).execute()
                    success("Cliente guardado")
                    st.rerun()

    with tab3_cli:
        df_cli_ed = get_clientes()
        if df_cli_ed.empty:
            st.info("Sin clientes registrados.")
        else:
            cli_opts = {f"{r['nombre']} ({r.get('rif_cedula','') or 'sin RIF'})": r
                        for _, r in df_cli_ed.iterrows()}
            cli_sel_ed = st.selectbox("Selecciona cliente", list(cli_opts.keys()), key="cli_ed_sel")
            cli_ed = cli_opts[cli_sel_ed]

            with st.form("form_editar_cliente"):
                c1, c2 = st.columns(2)
                ed_nombre = c1.text_input("Nombre / Razón social *", value=cli_ed.get("nombre",""))
                ed_rif    = c2.text_input("RIF / Cédula", value=cli_ed.get("rif_cedula","") or "")
                c3, c4 = st.columns(2)
                ed_tel   = c3.text_input("Teléfono", value=cli_ed.get("telefono","") or "")
                ed_email = c4.text_input("Email", value=cli_ed.get("email","") or "")
                ed_dir   = st.text_input("Dirección", value=cli_ed.get("direccion","") or "")
                ed_tipo  = st.selectbox("Tipo", ["Persona natural","Empresa","Distribuidor"],
                                        index=["Persona natural","Empresa","Distribuidor"].index(
                                            cli_ed.get("tipo","Persona natural"))
                                        if cli_ed.get("tipo") in ["Persona natural","Empresa","Distribuidor"] else 0)
                col_save, col_del = st.columns(2)
                btn_save = col_save.form_submit_button("💾 Guardar cambios", use_container_width=True, type="primary")
                btn_del  = col_del.form_submit_button("🗑️ Eliminar cliente", use_container_width=True)

            if btn_save:
                if not ed_nombre:
                    error("El nombre es obligatorio")
                else:
                    sb.table("dim_clientes").update({
                        "nombre": ed_nombre, "rif_cedula": ed_rif,
                        "telefono": ed_tel, "email": ed_email,
                        "direccion": ed_dir, "tipo": ed_tipo
                    }).eq("id", cli_ed["id"]).execute()
                    success(f"Cliente '{ed_nombre}' actualizado")
                    st.rerun()

            if btn_del:
                # Verificar ventas vinculadas por ID (no por nombre) para evitar falsos positivos con duplicados
                ventas_por_id = sb.table("fact_ventas").select("id").eq("cliente_id", cli_ed["id"]).execute()
                tiene_ventas = len(ventas_por_id.data) > 0 if ventas_por_id.data else False
                if tiene_ventas:
                    st.warning(f"⚠️ No se puede eliminar — '{cli_ed['nombre']}' tiene {len(ventas_por_id.data)} venta(s) vinculadas a este registro. Puedes editar su nombre si es necesario.")
                else:
                    sb.table("dim_clientes").delete().eq("id", cli_ed["id"]).execute()
                    success(f"Cliente eliminado")
                    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# FINANZAS
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "💰 Finanzas":
    st.title("💰 Finanzas")

    movs_df = get_movimientos()
    prods_fin = get_productos()

    ingresos = movs_df[movs_df["tipo"]=="ingreso"]["monto"].sum() if not movs_df.empty else 0
    egresos  = movs_df[movs_df["tipo"]=="egreso"]["monto"].sum()  if not movs_df.empty else 0
    balance  = ingresos - egresos

    # Retiros por persona
    ret_luifer = movs_df[movs_df["categoria"]=="Retiro Luifer"]["monto"].sum() if not movs_df.empty else 0
    ret_omar   = movs_df[movs_df["categoria"]=="Retiro Omar"]["monto"].sum()   if not movs_df.empty else 0

    # Valor del inventario
    val_inv = (prods_fin["stock_actual"] * prods_fin["precio_costo"]).sum() if not prods_fin.empty else 0

    # KPIs fila 1
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💵 Ingresos totales",  fmt_usd(ingresos))
    c2.metric("📤 Egresos totales",   fmt_usd(egresos))
    c3.metric("⚖️ Balance en caja",   fmt_usd(balance))
    c4.metric("📦 Valor inventario",  fmt_usd(val_inv), help="Stock actual × precio costo por producto")

    # KPIs fila 2 — retiros
    st.divider()
    st.caption("💸 Retiros de utilidades")
    r1, r2, r3 = st.columns(3)
    r1.metric("Retiro Luifer", fmt_usd(ret_luifer))
    r2.metric("Retiro Omar",   fmt_usd(ret_omar))
    r3.metric("Total retirado", fmt_usd(ret_luifer + ret_omar))

    st.divider()
    tab1, tab2, tab3_fin = st.tabs(["📋 Movimientos", "➕ Registro manual", "💸 Registrar retiro"])

    with tab1:
        if movs_df.empty:
            st.info("Sin movimientos registrados.")
        else:
            c1, c2 = st.columns(2)
            tipo_fil = c1.selectbox("Tipo", ["Todos","ingreso","egreso"])
            all_cats = ["Todas"] + sorted(movs_df["categoria"].dropna().unique().tolist())
            cat_fil  = c2.selectbox("Categoría", all_cats)

            fil = movs_df.copy()
            if tipo_fil != "Todos":  fil = fil[fil["tipo"] == tipo_fil]
            if cat_fil  != "Todas":  fil = fil[fil["categoria"] == cat_fil]

            fil["monto_fmt"] = fil.apply(
                lambda r: f"+{fmt_usd(r['monto'])}" if r["tipo"]=="ingreso" else f"-{fmt_usd(r['monto'])}", axis=1)
            st.dataframe(
                fil[["fecha","tipo","categoria","descripcion","monto_fmt"]].rename(columns={
                    "fecha":"Fecha","tipo":"Tipo","categoria":"Categoría",
                    "descripcion":"Descripción","monto_fmt":"Monto"}),
                use_container_width=True, hide_index=True)

            csv = fil.drop(columns=["monto_fmt"], errors="ignore").to_csv(index=False).encode("utf-8")
            st.download_button("📥 Exportar CSV", csv, "movimientos.csv", "text/csv")

    with tab2:
        with st.form("form_movimiento"):
            c1, c2 = st.columns(2)
            tipo   = c1.selectbox("Tipo", ["ingreso","egreso"])
            cat    = c2.selectbox("Categoría", ["Venta","Compra de mercancía","Inversión inicial",
                                                 "Gasto operativo","Transporte","Otro"])
            c3, c4 = st.columns(2)
            monto  = c3.number_input("Monto ($)", min_value=0.0, step=0.01)
            fecha  = c4.date_input("Fecha", value=date.today())
            desc   = st.text_input("Descripción")
            guardar = st.form_submit_button("💾 Registrar", use_container_width=True, type="primary")

        if guardar:
            if monto <= 0:
                error("El monto debe ser mayor a 0")
            else:
                registrar_movimiento(tipo, cat, monto, fecha, desc)
                st.success(f"✅ Movimiento registrado: {tipo} de {fmt_usd(monto)} en '{cat}'")
                st.rerun()

    with tab3_fin:
        st.subheader("💸 Registrar retiro de utilidades")
        st.caption("Cada retiro queda registrado como egreso y aparece en el historial individual de cada socio.")

        with st.form("form_retiro"):
            socio = st.radio("Socio", ["Luifer", "Omar"], horizontal=True)
            c1, c2 = st.columns(2)
            monto_ret = c1.number_input("Monto a retirar ($)", min_value=0.01, step=0.01)
            fecha_ret = c2.date_input("Fecha del retiro", value=date.today())
            desc_ret  = st.text_input("Nota (opcional)", placeholder="Ej: quincena mayo")
            btn_ret   = st.form_submit_button("💸 Registrar retiro", use_container_width=True, type="primary")

        if btn_ret:
            if monto_ret <= 0:
                error("El monto debe ser mayor a 0")
            else:
                # Advertencia informativa si el monto supera el balance, pero no bloquea
                # El balance contable incluye la inversión inicial como egreso,
                # por lo que puede diferir del efectivo físico disponible
                if monto_ret > balance and balance > 0:
                    st.toast(f"ℹ️ Nota: el monto supera el balance contable ({fmt_usd(balance)})", icon="ℹ️")
                cat_retiro = f"Retiro {socio}"
                desc_final = desc_ret if desc_ret else f"Retiro de utilidades — {socio}"
                registrar_movimiento("egreso", cat_retiro, monto_ret, fecha_ret, desc_final)
                success(f"Retiro de {fmt_usd(monto_ret)} registrado para {socio}")
                st.rerun()

        # Historial de retiros
        st.divider()
        st.subheader("📊 Historial de retiros")
        if not movs_df.empty:
            retiros = movs_df[movs_df["categoria"].isin(["Retiro Luifer","Retiro Omar"])].copy()
            if not retiros.empty:
                retiros["monto_fmt"] = retiros["monto"].apply(lambda x: f"-{fmt_usd(x)}")
                st.dataframe(
                    retiros[["fecha","categoria","descripcion","monto_fmt"]].rename(columns={
                        "fecha":"Fecha","categoria":"Socio","descripcion":"Nota","monto_fmt":"Monto"}),
                    use_container_width=True, hide_index=True)
                col_l, col_o, col_t = st.columns(3)
                col_l.metric("Total Luifer", fmt_usd(ret_luifer))
                col_o.metric("Total Omar",   fmt_usd(ret_omar))
                col_t.metric("Total socios", fmt_usd(ret_luifer + ret_omar))
            else:
                st.info("Sin retiros registrados aún.")
        else:
            st.info("Sin movimientos registrados.")

# ══════════════════════════════════════════════════════════════════════════════
# EXPORTAR DATOS
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "📤 Exportar datos":
    st.title("📤 Exportar datos")
    st.caption("Descarga cualquier tabla en CSV — compatible con Excel. Úsalo como respaldo mensual o para análisis.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📦 Inventario")
        if st.button("Generar", key="exp_inv"):
            df = get_productos()
            if not df.empty:
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Descargar inventario.csv", csv, "inventario.csv", "text/csv", key="dl_inv")
            else:
                st.info("Sin datos.")

        st.subheader("🛒 Ventas")
        if st.button("Generar", key="exp_ven"):
            df = get_ventas()
            if not df.empty:
                df["cliente_nombre"] = df["dim_clientes"].apply(
                    lambda x: x["nombre"] if isinstance(x, dict) else "Cliente directo")
                df = df.drop(columns=["dim_clientes"], errors="ignore")
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Descargar ventas.csv", csv, "ventas.csv", "text/csv", key="dl_ven")
            else:
                st.info("Sin datos.")

        st.subheader("👥 Clientes")
        if st.button("Generar", key="exp_cli"):
            df = get_clientes()
            if not df.empty:
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Descargar clientes.csv", csv, "clientes.csv", "text/csv", key="dl_cli")
            else:
                st.info("Sin datos.")

    with col2:
        st.subheader("🚚 Pedidos")
        if st.button("Generar", key="exp_ped"):
            df = get_pedidos()
            if not df.empty:
                df["proveedor_nombre"] = df.apply(
                    lambda r: r["dim_proveedores"]["nombre"] if isinstance(r.get("dim_proveedores"), dict)
                    else r.get("proveedor_nombre","—"), axis=1)
                df = df.drop(columns=["dim_proveedores"], errors="ignore")
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Descargar pedidos.csv", csv, "pedidos.csv", "text/csv", key="dl_ped")
            else:
                st.info("Sin datos.")

        st.subheader("💰 Movimientos financieros")
        if st.button("Generar", key="exp_mov"):
            df = get_movimientos()
            if not df.empty:
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Descargar movimientos.csv", csv, "movimientos.csv", "text/csv", key="dl_mov")
            else:
                st.info("Sin datos.")

        st.subheader("📊 Profit por venta (detalle)")
        if st.button("Generar", key="exp_profit"):
            todos = get_todas_venta_items()
            ventas = get_ventas()
            if not todos.empty and not ventas.empty:
                todos = calcular_profit_items(todos)
                todos["producto"] = todos["dim_productos"].apply(
                    lambda x: f"{x['codigo']} — {x['descripcion']}" if isinstance(x, dict) else "—")
                fecha_map = ventas.set_index("id")["fecha"].to_dict()
                cliente_map = ventas.set_index("id")["dim_clientes"].apply(
                    lambda x: x["nombre"] if isinstance(x, dict) else "Cliente directo").to_dict()
                todos["fecha_venta"]   = todos["venta_id"].map(fecha_map)
                todos["cliente"]       = todos["venta_id"].map(cliente_map)
                export = todos[["fecha_venta","cliente","producto","cantidad",
                                "precio_unitario","costo_unit","subtotal","profit","margen_pct"]].copy()
                export.columns = ["Fecha","Cliente","Producto","Cantidad",
                                  "P.Venta","Costo u.","Subtotal","Profit","Margen %"]
                csv = export.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Descargar profit_detalle.csv", csv, "profit_detalle.csv", "text/csv", key="dl_profit")
            else:
                st.info("Sin datos.")

    st.divider()
    st.info("💡 **Consejo:** Exporta inventario, ventas y profit una vez al mes y guárdalos en una carpeta de OneDrive como respaldo.")
