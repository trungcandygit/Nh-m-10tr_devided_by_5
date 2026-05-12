"""Trang 1 — Tổng quan KPI & Xu hướng doanh thu"""
import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from data_loader import DATA, BRAND, GROUP_NAMES

def _fmt_b(v):
    return f"{v/1e9:.1f} tỷ"

def _fmt_k(v):
    if v >= 1e9: return f"{v/1e9:.1f}B"
    if v >= 1e6: return f"{v/1e6:.1f}M"
    return f"{v:,.0f}"

def _kpi_card(label, value, sub="", accent="#1D9E75"):
    return dbc.Col(html.Div([
        html.Div(label, className="kpi-label"),
        html.Div(value, className="kpi-value"),
        html.Div(sub,   className="kpi-sub"),
    ], className="kpi-card", style={"borderLeftColor": accent}), md=3)


def layout():
    kpi = DATA["kpi"].set_index("kpi")
    monthly = DATA["monthly"].copy()
    monthly["ym_dt"] = pd.to_datetime(monthly["ym"] + "-01")

    def val(k):
        return float(kpi.loc[k, "value"]) if k in kpi.index else 0

    # ─── KPI row
    kpi_row = dbc.Row([
        _kpi_card("Tổng doanh thu (Jan25–Mar26)",  _fmt_b(val("total_revenue")),
                  f"T3/2026: {_fmt_b(val('revenue_t3'))}"),
        _kpi_card("Số đơn hàng",  f"{int(val('total_orders')):,}",
                  f"{int(val('total_order_lines')):,} dòng hàng", accent="#378ADD"),
        _kpi_card("Đại lý hoạt động",  f"{int(val('active_dealers')):,}",
                  f"{int(val('sku_count')):,} SKU", accent="#7F77DD"),
        _kpi_card("Tỉ lệ xử lý email T3",  f"{val('t3_success_rate'):.1f}%",
                  f"{int(val('t3_orders_processed')):,} đơn thành công", accent="#D85A30"),
    ])

    # ─── Monthly revenue by group
    groups = monthly["group_code"].unique()
    traces_rev = []
    for gc in groups:
        df = monthly[monthly["group_code"] == gc].sort_values("ym_dt")
        traces_rev.append(go.Scatter(
            x=df["ym_dt"], y=df["revenue"],
            mode="lines+markers", name=GROUP_NAMES.get(gc, gc),
            line=dict(color=BRAND.get(gc, "#999"), width=2.5),
            marker=dict(size=5),
            hovertemplate="<b>%{x|%b %Y}</b><br>Doanh thu: %{y:,.0f} VND<extra></extra>"
        ))
    fig_rev = go.Figure(traces_rev)
    fig_rev.update_layout(
        xaxis_title="", yaxis_title="Doanh thu (VND)",
        legend=dict(orientation="h", y=-0.2),
        plot_bgcolor="#f8f8f8", paper_bgcolor="#fff",
        margin=dict(l=10, r=10, t=10, b=40), height=320,
        yaxis=dict(tickformat=",.0s"),
    )

    # ─── Monthly quantity stacked bar
    traces_qty = []
    for gc in groups:
        df = monthly[monthly["group_code"] == gc].sort_values("ym_dt")
        traces_qty.append(go.Bar(
            x=df["ym_dt"], y=df["quantity"],
            name=GROUP_NAMES.get(gc, gc),
            marker_color=BRAND.get(gc, "#999"),
            hovertemplate="<b>%{x|%b %Y}</b><br>Sản lượng: %{y:,}<extra></extra>"
        ))
    fig_qty = go.Figure(traces_qty)
    fig_qty.update_layout(
        barmode="stack", xaxis_title="", yaxis_title="Sản lượng (chiếc)",
        legend=dict(orientation="h", y=-0.2),
        plot_bgcolor="#f8f8f8", paper_bgcolor="#fff",
        margin=dict(l=10, r=10, t=10, b=40), height=300,
    )

    # ─── YoY bar
    yoy_df = monthly[monthly["yoy_revenue_pct"].notna()].copy()
    yoy_df = yoy_df[yoy_df["fiscal_year"] == 2026]
    yoy_agg = yoy_df.groupby("ym")["revenue"].sum().reset_index()
    yoy_base = monthly[(monthly["fiscal_year"]==2025) & (monthly["ym"].str.startswith("2025-0"))].groupby(
        monthly["fiscal_month"])["revenue"].sum().reset_index()
    # Simple YoY comparison 2025 vs 2026 Q1
    q1_2025 = monthly[(monthly["fiscal_year"]==2025) & (monthly["fiscal_month"]<=3)].groupby(
        ["fiscal_month","group_code"])["revenue"].sum().reset_index()
    q1_2026 = monthly[(monthly["fiscal_year"]==2026) & (monthly["fiscal_month"]<=3)].groupby(
        ["fiscal_month","group_code"])["revenue"].sum().reset_index()
    q1_2025["label"] = q1_2025["fiscal_month"].map({1:"T1",2:"T2",3:"T3"}) + "/2025"
    q1_2026["label"] = q1_2026["fiscal_month"].map({1:"T1",2:"T2",3:"T3"}) + "/2026"
    cmp = pd.concat([q1_2025, q1_2026])
    fig_yoy = px.bar(cmp, x="label", y="revenue", color="group_code",
                     color_discrete_map=BRAND, barmode="group",
                     labels={"revenue":"Doanh thu","label":"Tháng","group_code":"Nhóm SP"})
    fig_yoy.update_layout(
        plot_bgcolor="#f8f8f8", paper_bgcolor="#fff",
        margin=dict(l=10, r=10, t=10, b=10), height=280,
        yaxis=dict(tickformat=",.0s"),
        legend=dict(orientation="h", y=-0.25),
    )

    return html.Div([
        html.Div([
            html.H4("Tổng quan kinh doanh"),
            html.P("Jan 2025 – Mar 2026 | 702 đại lý | 247 SKU | 5 nhóm sản phẩm"),
        ], className="page-header"),

        kpi_row,

        dbc.Row([
            dbc.Col(html.Div([
                html.Div("Xu hướng doanh thu theo nhóm sản phẩm", className="chart-title"),
                dcc.Graph(figure=fig_rev, config={"displayModeBar": False}),
            ], className="chart-card"), md=8),
            dbc.Col(html.Div([
                html.Div("Sản lượng theo tháng (stacked)", className="chart-title"),
                dcc.Graph(figure=fig_qty, config={"displayModeBar": False}),
            ], className="chart-card"), md=4),
        ]),

        dbc.Row([
            dbc.Col(html.Div([
                html.Div("So sánh Q1-2025 vs Q1-2026 (Grouped bar)", className="chart-title"),
                dcc.Graph(figure=fig_yoy, config={"displayModeBar": False}),
            ], className="chart-card"), md=12),
        ]),

        html.Div("Xe đạp Thống Nhất • DATA EXPLORERS 2026", className="watermark"),
    ], style={"padding": "20px"})