import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
from datetime import date, datetime
import uuid

# ── CONFIG ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Inventario Herrajes",
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
    r = sb.table("fact_venta_items").select("*, dim_productos(codigo, descripcion)").eq("venta_id", venta_id).execute()
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
            "fecha": str(d),
            "anio": d.year, "mes": d.month, "dia": d.day,
            "mes_nombre": d.strftime("%B"),
            "trimestre": f"Q{(d.month-1)//3+1}"
        }).execute()

def registrar_movimiento(tipo, categoria, monto, fecha, descripcion, ref_id=None):
    ensure_fecha(fecha)
    sb.table("fact_movimientos").insert({
        "id": str(uuid.uuid4()),
        "fecha": str(fecha), "tipo": tipo,
        "categoria": categoria, "monto": float(monto),
        "descripcion": descripcion,
        "referencia_id": str(ref_id) if ref_id else None
    }).execute()

# ── ESTILO ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.6rem !important; }
[data-testid="stMetricLabel"] { font-size: 0.85rem !important; color: #888; }
.stTabs [data-baseweb="tab"] { font-size: 1rem; padding: 8px 20px; }
div[data-testid="stExpander"] { border: 1px solid #333; border-radius: 8px; }
.stDataFrame { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/ios-filled/100/wrench.png", width=48)
    st.title("Herrajes & Baños")
    st.caption("Sistema de inventario")
    st.divider()
    pagina = st.radio("Navegación", [
        "🏠 Dashboard",
        "📦 Inventario",
        "🛒 Nueva Venta",
        "📋 Historial Ventas",
        "🚚 Pedidos",
        "👥 Clientes",
        "💰 Finanzas",
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

    # KPIs
    ingresos = movs_df[movs_df["tipo"]=="ingreso"]["monto"].sum() if not movs_df.empty else 0
    egresos  = movs_df[movs_df["tipo"]=="egreso"]["monto"].sum()  if not movs_df.empty else 0
    balance  = ingresos - egresos
    n_ventas = len(ventas_df[ventas_df["estado"]=="Completada"]) if not ventas_df.empty else 0
    stock_bajo = len(productos_df[productos_df["stock_actual"] <= productos_df["stock_minimo"]]) if not productos_df.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💵 Ingresos", fmt_usd(ingresos))
    c2.metric("📤 Egresos",  fmt_usd(egresos))
    c3.metric("⚖️ Balance",  fmt_usd(balance), delta=fmt_usd(balance))
    c4.metric("🛒 Ventas completadas", n_ventas)

    st.divider()
    col1, col2 = st.columns([2,1])

    with col1:
        st.subheader("📊 Ventas recientes")
        if not ventas_df.empty:
            recent = ventas_df.head(10).copy()
            recent["cliente"] = recent["dim_clientes"].apply(
                lambda x: x["nombre"] if isinstance(x, dict) else "Cliente directo")
            recent["total_fmt"] = recent["total"].apply(fmt_usd)
            st.dataframe(
                recent[["fecha","cliente","total_fmt","estado"]].rename(columns={
                    "fecha":"Fecha","cliente":"Cliente",
                    "total_fmt":"Total","estado":"Estado"}),
                use_container_width=True, hide_index=True)
        else:
            st.info("Sin ventas registradas aún.")

    with col2:
        st.subheader("⚠️ Stock bajo")
        if not productos_df.empty:
            bajos = productos_df[productos_df["stock_actual"] <= productos_df["stock_minimo"]]
            if not bajos.empty:
                for _, p in bajos.iterrows():
                    color = "🔴" if p["stock_actual"] == 0 else "🟡"
                    st.write(f"{color} **{p['codigo']}** — {p['stock_actual']} uds")
            else:
                st.success("✅ Todo el stock en orden")
        else:
            st.info("Sin productos cargados.")

    # Gráfico ventas por categoría
    if not ventas_df.empty and not productos_df.empty:
        st.divider()
        st.subheader("🏆 Ingresos por mes")
        movs_ing = movs_df[movs_df["tipo"]=="ingreso"].copy() if not movs_df.empty else pd.DataFrame()
        if not movs_ing.empty:
            movs_ing["fecha"] = pd.to_datetime(movs_ing["fecha"])
            movs_ing["mes"] = movs_ing["fecha"].dt.strftime("%Y-%m")
            por_mes = movs_ing.groupby("mes")["monto"].sum().reset_index()
            fig = px.bar(por_mes, x="mes", y="monto", labels={"mes":"Mes","monto":"Ingresos ($)"},
                        color_discrete_sequence=["#d4860a"])
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                             showlegend=False, margin=dict(l=0,r=0,t=20,b=0))
            st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# INVENTARIO
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "📦 Inventario":
    st.title("📦 Inventario")

    tab1, tab2 = st.tabs(["📋 Ver inventario", "➕ Agregar / Editar producto"])

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
                lambda r: "🔴 Agotado" if r["stock_actual"]==0
                else ("🟡 Bajo" if r["stock_actual"]<=r["stock_minimo"] else "🟢 OK"), axis=1)

            st.dataframe(
                fil[["codigo","descripcion","categoria","stock_actual","stock_minimo",
                     "precio_costo","precio_venta","margen","stock_status","unidad"]].rename(columns={
                    "codigo":"Código","descripcion":"Descripción","categoria":"Categoría",
                    "stock_actual":"Stock","stock_minimo":"Mín.","precio_costo":"Costo $",
                    "precio_venta":"Venta $","margen":"Margen","stock_status":"Estado","unidad":"Unidad"}),
                use_container_width=True, hide_index=True)

            st.divider()
            st.subheader("⬇️ Exportar")
            csv = fil.to_csv(index=False).encode("utf-8")
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
                st.info(f"📊 Margen: **{margen:.1f}%** — Ganancia por unidad: **{fmt_usd(pventa-costo)}**")

            guardar = st.form_submit_button("💾 Guardar producto", use_container_width=True, type="primary")

        if guardar:
            if not codigo or not desc:
                error("Código y descripción son obligatorios")
            else:
                data = {"codigo": codigo.upper(), "descripcion": desc, "categoria": cat,
                        "stock_actual": stock, "stock_minimo": stock_min,
                        "precio_costo": costo, "precio_venta": pventa, "unidad": unidad}
                if modo == "Editar existente" and prod_sel is not None:
                    sb.table("dim_productos").update(data).eq("id", prod_sel["id"]).execute()
                    success("Producto actualizado")
                else:
                    data["id"] = str(uuid.uuid4())
                    sb.table("dim_productos").insert(data).execute()
                    success("Producto agregado")
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# NUEVA VENTA
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "🛒 Nueva Venta":
    st.title("🛒 Nueva Venta")

    productos_df = get_productos()
    clientes_df  = get_clientes()

    if productos_df.empty:
        st.warning("⚠️ No hay productos en inventario. Agrega productos primero.")
        st.stop()

    # Estado de la venta en sesión
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

    # Selector de producto
    prods_opts = {f"{r['codigo']} — {r['descripcion']} (Stock: {r['stock_actual']})": r
                  for _, r in productos_df.iterrows()}
    pc1, pc2, pc3 = st.columns([3,1,1])
    prod_elegido = pc1.selectbox("Producto", list(prods_opts.keys()), label_visibility="collapsed")
    prod_data = prods_opts[prod_elegido]
    cantidad  = pc2.number_input("Cant.", min_value=1, max_value=int(prod_data["stock_actual"]) if prod_data["stock_actual"] > 0 else 999, value=1)
    precio_u  = pc3.number_input("Precio $", min_value=0.0, step=0.01, value=float(prod_data["precio_venta"]))

    if st.button("➕ Agregar a la venta", use_container_width=True):
        existing = next((i for i in st.session_state.items_venta if i["producto_id"] == prod_data["id"]), None)
        if existing:
            existing["cantidad"] += cantidad
            existing["subtotal"] = existing["cantidad"] * existing["precio_unitario"]
        else:
            st.session_state.items_venta.append({
                "producto_id": prod_data["id"],
                "codigo": prod_data["codigo"],
                "descripcion": prod_data["descripcion"],
                "cantidad": cantidad,
                "precio_unitario": precio_u,
                "subtotal": cantidad * precio_u
            })
        st.rerun()

    # Tabla de items
    if st.session_state.items_venta:
        st.divider()
        st.subheader("🧾 Productos en esta venta")
        items_df = pd.DataFrame(st.session_state.items_venta)
        items_display = items_df[["codigo","descripcion","cantidad","precio_unitario","subtotal"]].copy()
        items_display.columns = ["Código","Descripción","Cantidad","Precio u.","Subtotal"]
        items_display["Precio u."] = items_display["Precio u."].apply(fmt_usd)
        items_display["Subtotal"]  = items_display["Subtotal"].apply(fmt_usd)
        st.dataframe(items_display, use_container_width=True, hide_index=True)

        total = sum(i["subtotal"] for i in st.session_state.items_venta)
        st.markdown(f"### 💵 Total: **{fmt_usd(total)}**")

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
                    "total": total, "notas": notas_venta
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
                        # Leer stock real desde DB en el momento exacto de guardar
                        prod_real = sb.table("dim_productos").select("stock_actual").eq("id", item["producto_id"]).execute()
                        stock_real = prod_real.data[0]["stock_actual"] if prod_real.data else 0
                        sb.table("dim_productos").update({
                            "stock_actual": stock_real - item["cantidad"]
                        }).eq("id", item["producto_id"]).execute()

                if estado_venta == "Completada":
                    registrar_movimiento("ingreso","Venta", total, fecha_venta,
                                        f"Venta {venta_id[:8]} — {cliente_sel}", venta_id)

                st.session_state.items_venta = []
                success("Venta registrada exitosamente")
                st.rerun()
            except Exception as e:
                error(f"Error al guardar: {e}")
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

    # Detalle de venta
    st.divider()
    st.subheader("🔍 Ver detalle de venta")
    if not fil.empty:
        venta_opts = {f"{r['fecha']} — {r['cliente_nombre']} — {fmt_usd(r['total'])}": r["id"]
                      for _, r in fil.iterrows()}
        venta_sel = st.selectbox("Selecciona venta", list(venta_opts.keys()))
        items = get_venta_items(venta_opts[venta_sel])
        if not items.empty:
            items["producto"] = items["dim_productos"].apply(
                lambda x: f"{x['codigo']} — {x['descripcion']}" if isinstance(x, dict) else "—")
            items["subtotal_fmt"] = items["subtotal"].apply(fmt_usd)
            st.dataframe(items[["producto","cantidad","precio_unitario","subtotal_fmt"]].rename(columns={
                "producto":"Producto","cantidad":"Cantidad",
                "precio_unitario":"Precio u.","subtotal_fmt":"Subtotal"}),
                use_container_width=True, hide_index=True)

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

        # Tabla masiva de productos
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
            use_container_width=True,
            hide_index=True,
            disabled=["Código","Descripción","Stock actual","Stock mínimo","Sugerido"],
            column_config={
                "Pedir": st.column_config.NumberColumn("Pedir", min_value=0, step=1),
                "Costo unit. $": st.column_config.NumberColumn("Costo unit. $", min_value=0.0, step=0.01, format="$%.2f"),
            }
        )

        items_pedido = edited[edited["Pedir"] > 0]
        if not items_pedido.empty:
            total_ped = (items_pedido["Pedir"] * items_pedido["Costo unit. $"]).sum()
            st.metric(f"Total estimado del pedido ({len(items_pedido)} productos)", fmt_usd(total_ped))

        if st.button("✅ Registrar pedido", type="primary", use_container_width=True):
            if items_pedido.empty:
                warn("Agrega al menos un producto con cantidad > 0")
            elif not prov_nombre:
                warn("Ingresa el nombre del proveedor")
            else:
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
                        "fecha": str(fecha_ped),
                        "fecha_eta": str(fecha_eta),
                        "estado": "Pendiente",
                        "total": float(total_ped)
                    }).execute()

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

                    registrar_movimiento("egreso","Compra de mercancía", total_ped,
                                        fecha_ped, f"Pedido {pedido_id[:8]} — {prov_nombre}", pedido_id)
                    success("Pedido registrado")
                    st.rerun()
                except Exception as e:
                    error(f"Error: {e}")

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

        fil_ped_display = fil_ped[["fecha","proveedor","fecha_eta","total","estado"]].copy()
        fil_ped_display.columns = ["Fecha","Proveedor","ETA","Total","Estado"]
        fil_ped_display["Total"] = fil_ped_display["Total"].apply(fmt_usd)
        st.dataframe(fil_ped_display, use_container_width=True, hide_index=True)

        csv_ped = fil_ped.drop(columns=["dim_proveedores"], errors="ignore").to_csv(index=False).encode("utf-8")
        st.download_button("📥 Exportar CSV", csv_ped, "pedidos.csv", "text/csv")

        st.divider()
        st.subheader("🔍 Ver detalle de pedido")
        if not fil_ped.empty:
            ped_opts_all = {f"{r['fecha']} — {r['proveedor']} — {fmt_usd(r['total'])} [{r['estado']}]": r["id"]
                           for _, r in fil_ped.iterrows()}
            ped_det_sel = st.selectbox("Selecciona pedido", list(ped_opts_all.keys()), key="ped_det_sel")
            ped_det_id = ped_opts_all[ped_det_sel]

            items_det = get_pedido_items(ped_det_id)
            if not items_det.empty:
                items_det["Producto"] = items_det["dim_productos"].apply(
                    lambda x: f"{x['codigo']} — {x['descripcion']}" if isinstance(x, dict) else "—")
                items_det["Costo u."] = items_det["costo_unitario"].apply(fmt_usd)
                items_det["Subtotal $"] = items_det["subtotal"].apply(fmt_usd)
                st.dataframe(
                    items_det[["Producto","cantidad","Costo u.","Subtotal $"]].rename(columns={"cantidad":"Cantidad"}),
                    use_container_width=True, hide_index=True)
                st.metric("Total del pedido", fmt_usd(items_det["subtotal"].sum()))

            ped_row = fil_ped[fil_ped["id"] == ped_det_id].iloc[0]
            if ped_row["estado"] == "Pendiente":
                st.divider()
                if st.button("✅ Marcar como recibido — actualiza stock", type="primary", use_container_width=True):
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
            else:
                st.info(f"Este pedido ya está marcado como **{ped_row['estado']}**.")

# ══════════════════════════════════════════════════════════════════════════════
# CLIENTES
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "👥 Clientes":
    st.title("👥 Clientes")

    tab1, tab2 = st.tabs(["📋 Ver clientes", "➕ Agregar cliente"])

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
                sb.table("dim_clientes").insert({
                    "id": str(uuid.uuid4()), "nombre": nombre, "rif_cedula": rif,
                    "telefono": tel, "email": email, "direccion": dir_, "tipo": tipo
                }).execute()
                success("Cliente guardado")
                st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# FINANZAS
# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "💰 Finanzas":
    st.title("💰 Finanzas")

    movs_df = get_movimientos()

    ingresos = movs_df[movs_df["tipo"]=="ingreso"]["monto"].sum() if not movs_df.empty else 0
    egresos  = movs_df[movs_df["tipo"]=="egreso"]["monto"].sum()  if not movs_df.empty else 0
    balance  = ingresos - egresos

    c1, c2, c3 = st.columns(3)
    c1.metric("💵 Ingresos totales", fmt_usd(ingresos))
    c2.metric("📤 Egresos totales",  fmt_usd(egresos))
    c3.metric("⚖️ Balance neto",     fmt_usd(balance), delta=fmt_usd(balance))

    st.divider()
    tab1, tab2 = st.tabs(["📋 Movimientos", "➕ Registro manual"])

    with tab1:
        if movs_df.empty:
            st.info("Sin movimientos registrados.")
        else:
            c1, c2 = st.columns(2)
            tipo_fil = c1.selectbox("Tipo", ["Todos","ingreso","egreso"])
            cat_fil  = c2.selectbox("Categoría", ["Todas"] + sorted(movs_df["categoria"].unique().tolist()))

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
                success("Movimiento registrado")
                st.rerun()
