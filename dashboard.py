"""
dashboard.py — CyberDay Price Tracker Dashboard
Corre con: streamlit run dashboard.py
"""
from db import get_all_history
import pandas as pd
import streamlit as st
import sqlite3
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os

# ─────────────────────────────────────────────
# Config página
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="CyberDay Tracker",
    page_icon="🖥️",
    layout="wide",
)

# ─────────────────────────────────────────────
# Estilos
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background-color: #0a0a0f;
    color: #e8e8f0;
}

.main { background-color: #0a0a0f; }

h1, h2, h3 { font-family: 'Syne', sans-serif; font-weight: 800; }

.metric-card {
    background: linear-gradient(135deg, #12121a 0%, #1a1a2e 100%);
    border: 1px solid #2a2a3e;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #6c63ff, #ff6584);
}
.metric-card.alert::before {
    background: linear-gradient(90deg, #00ff88, #00d4ff);
    animation: pulse 1.5s ease-in-out infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

.store-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    font-family: 'Space Mono', monospace;
}
.badge-falabella { background: #1a0a2e; color: #b388ff; border: 1px solid #6c63ff; }
.badge-ripley    { background: #1a0a0a; color: #ff8a80; border: 1px solid #ff5252; }
.badge-paris     { background: #0a1a0a; color: #69f0ae; border: 1px solid #00e676; }

.price-big {
    font-family: 'Space Mono', monospace;
    font-size: 32px;
    font-weight: 700;
    color: #ffffff;
    line-height: 1;
}
.price-old {
    font-family: 'Space Mono', monospace;
    font-size: 14px;
    color: #555570;
    text-decoration: line-through;
}
.discount-tag {
    display: inline-block;
    background: #00ff8820;
    color: #00ff88;
    border: 1px solid #00ff8840;
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 13px;
    font-weight: 700;
    font-family: 'Space Mono', monospace;
}
.discount-fake {
    background: #ff525220;
    color: #ff5252;
    border-color: #ff525240;
}
.product-name {
    font-size: 14px;
    color: #9090b0;
    margin-bottom: 8px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.stat-row {
    display: flex;
    gap: 24px;
    margin-top: 12px;
}
.stat-item {
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    color: #555570;
}
.stat-item span {
    color: #9090b0;
    display: block;
    font-size: 13px;
}
.header-title {
    font-size: 42px;
    font-weight: 800;
    background: linear-gradient(90deg, #ffffff 0%, #9090d0 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.1;
    margin-bottom: 4px;
}
.header-sub {
    color: #555570;
    font-size: 14px;
    font-family: 'Space Mono', monospace;
}
.no-data {
    text-align: center;
    padding: 60px 20px;
    color: #555570;
    font-family: 'Space Mono', monospace;
    font-size: 13px;
}
.section-title {
    font-size: 11px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #555570;
    font-family: 'Space Mono', monospace;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid #1a1a2e;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Helpers BD
# ─────────────────────────────────────────────
DB_PATH = "prices.db"

def load_data():
    rows = get_all_history()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="mixed")
    df["price"] = df["price"].astype(int)
    return df


def get_summary(df):
    """Resumen por producto: precio actual, máximo, mínimo, descuento real."""
    if df.empty:
        return []
    results = []
    for url, group in df.groupby("product_url"):
        group = group.sort_values("timestamp")
        current = group.iloc[-1]["price"]
        max_p   = group["price"].max()
        min_p   = group["price"].min()
        store   = group.iloc[-1]["store"]
        name    = group.iloc[-1]["product_name"] or "Sin nombre"
        count   = len(group)
        last_ts = group.iloc[-1]["timestamp"]
        discount = round((max_p - current) / max_p * 100, 1) if max_p > 0 else 0
        results.append({
            "url": url, "store": store, "name": name,
            "current": current, "max": max_p, "min": min_p,
            "discount": discount, "count": count, "last_ts": last_ts,
            "history": group[["timestamp", "price"]],
        })
    return results


def format_clp(n):
    return f"${n:,.0f}".replace(",", ".")


# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.markdown('<div class="header-title">CyberDay Tracker</div>', unsafe_allow_html=True)
    st.markdown('<div class="header-sub">Monitoreo de precios en tiempo real · Falabella, Ripley, Paris</div>', unsafe_allow_html=True)

with col_h2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("↻  Actualizar datos", use_container_width=True):
        st.rerun()
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    st.markdown(f'<div style="font-family:Space Mono,monospace;font-size:11px;color:#555570;text-align:right">{now}</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Cargar datos
from db import init_db, get_all_history
init_db()  # crea la tabla si no existe
df = load_data()
summary = get_summary(df)

if not summary:
    st.markdown("""
    <div class="no-data">
        <div style="font-size:48px;margin-bottom:16px">📭</div>
        <div>Sin datos aún. Ejecuta <code>python tracker.py</code> para empezar.</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ─────────────────────────────────────────────
# KPIs globales
# ─────────────────────────────────────────────
total_products  = len(summary)
real_discounts  = [p for p in summary if p["discount"] >= 5]
best            = min(summary, key=lambda x: x["current"]) if summary else None
total_records   = len(df)

k1, k2, k3, k4 = st.columns(4)
kpi_style = "background:#12121a;border:1px solid #2a2a3e;border-radius:10px;padding:16px 20px;text-align:center"
num_style  = "font-family:Space Mono,monospace;font-size:28px;font-weight:700;color:#fff"
lab_style  = "font-size:11px;color:#555570;text-transform:uppercase;letter-spacing:0.1em;font-family:Space Mono,monospace"

with k1:
    st.markdown(f'<div style="{kpi_style}"><div style="{num_style}">{total_products}</div><div style="{lab_style}">Productos</div></div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div style="{kpi_style}"><div style="{num_style};color:#00ff88">{len(real_discounts)}</div><div style="{lab_style}">Ofertas reales</div></div>', unsafe_allow_html=True)
with k3:
    best_price = format_clp(best["current"]) if best else "-"
    st.markdown(f'<div style="{kpi_style}"><div style="{num_style};font-size:20px">{best_price}</div><div style="{lab_style}">Mejor precio</div></div>', unsafe_allow_html=True)
with k4:
    st.markdown(f'<div style="{kpi_style}"><div style="{num_style}">{total_records}</div><div style="{lab_style}">Mediciones</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Tarjetas de productos
# ─────────────────────────────────────────────
st.markdown('<div class="section-title">Productos en seguimiento</div>', unsafe_allow_html=True)

cols = st.columns(min(len(summary), 3))
for i, p in enumerate(summary):
    with cols[i % 3]:
        is_real   = p["discount"] >= 5
        card_cls  = "metric-card alert" if is_real else "metric-card"
        badge_cls = f"badge-{p['store']}"
        disc_cls  = "discount-tag" if is_real else "discount-tag discount-fake"
        disc_txt  = f"-{p['discount']}% REAL" if is_real else f"-{p['discount']}% dudoso"
        ago       = (datetime.now() - p["last_ts"].to_pydatetime()).seconds // 60

        st.markdown(f"""
        <div class="{card_cls}">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                <span class="store-badge {badge_cls}">{p['store']}</span>
                <span class="{disc_cls}">{disc_txt}</span>
            </div>
            <div class="product-name">{p['name'][:60]}</div>
            <div class="price-big">{format_clp(p['current'])}</div>
            <div class="price-old">máx. histórico: {format_clp(p['max'])}</div>
            <div class="stat-row">
                <div class="stat-item">MÍNIMO<span>{format_clp(p['min'])}</span></div>
                <div class="stat-item">MEDICIONES<span>{p['count']}</span></div>
                <div class="stat-item">ÚLTIMA VEZ<span>hace {ago} min</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Gráficos de historial
# ─────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-title">Historial de precios</div>', unsafe_allow_html=True)

for p in summary:
    hist = p["history"]
    if len(hist) < 2:
        continue

    fig = go.Figure()

    # Línea de precio
    fig.add_trace(go.Scatter(
        x=hist["timestamp"], y=hist["price"],
        mode="lines+markers",
        line=dict(color="#6c63ff", width=2),
        marker=dict(size=6, color="#6c63ff"),
        fill="tozeroy",
        fillcolor="rgba(108,99,255,0.07)",
        name="Precio",
        hovertemplate="<b>%{x|%d/%m %H:%M}</b><br>$%{y:,.0f}<extra></extra>",
    ))

    # Línea de precio máximo (referencia)
    fig.add_hline(
        y=p["max"], line_dash="dot",
        line_color="#ff6584", opacity=0.5,
        annotation_text=f"Máx. {format_clp(p['max'])}",
        annotation_font_color="#ff6584",
        annotation_font_size=11,
    )

    fig.update_layout(
        title=dict(text=p["name"][:55], font=dict(size=13, color="#9090b0"), x=0),
        paper_bgcolor="#12121a",
        plot_bgcolor="#12121a",
        font=dict(family="Space Mono, monospace", color="#9090b0"),
        xaxis=dict(gridcolor="#1a1a2e", showgrid=True, zeroline=False),
        yaxis=dict(gridcolor="#1a1a2e", showgrid=True, zeroline=False,
                   tickformat="$,.0f"),
        margin=dict(l=20, r=20, t=40, b=20),
        height=220,
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:40px 0 20px;font-family:Space Mono,monospace;
font-size:11px;color:#2a2a3e">
    CyberDay Tracker · descuento real = bajada vs precio máximo histórico
</div>
""", unsafe_allow_html=True)
