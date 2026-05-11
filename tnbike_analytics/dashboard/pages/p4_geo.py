"""Trang 4 — Địa lý: tỉnh thành & vùng"""
import dash_bootstrap_components as dbc
from dash import html, dcc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from data_loader import DATA, BRAND, GROUP_NAMES

REGION_COLORS = {
    "Miền Bắc": "#378ADD",
    "Miền Trung": "#BA7517",
    "Miền Nam": "#1D9E75",
    "Tây Nguyên": "#7F77DD",
}

def layout():
    prov  = DATA["province"].copy()
    reg   = DATA["region"].copy()

    # ─── Top 20 provinces bar chart
    top20 = prov.nlargest(20, "revenue").copy()
    top20["rev_b"] = top20["revenue"] / 1e9
    fig_prov = go.Figure(go.Bar(
        x=top20["rev_b"],
        y=top20["province_name"],
        orientation="h",
        marker_color=[REGION_COLORS.get(r,"#999") for r in top20["region"]],
        text=top20["rev_b"].map("{:.1f}".format),
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Doanh thu: %{x:.1f} tỷ<extra></extra>",
    ))
    fig_prov.update_layout(
        xaxis_title="Doanh thu (tỷ VND)", yaxis_title="",
        plot_bgcolor="#f8f8f8", paper_bgcolor="#fff",
        margin=dict(l=120, r=60, t=10, b=40), height=480,
        yaxis=dict(autorange="reversed"),
        showlegend=False,
    )

    # ─── Region donut
    fig_reg_donut = go.Figure(go.Pie(
        labels=reg["region"],
        values=reg["revenue"],
        hole=0.5,
        marker_colors=[REGION_COLORS.get(r,"#999") for r in reg["region"]],
        textinfo="label+percent",
        hovertemplate="%{label}: %{value:,.0f} VND<extra></extra>",
    ))
    fig_reg_donut.update_layout(
        showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10), height=300,
        paper_bgcolor="#fff",
    )

    # ─── Region stacked bar by group
    if "group_code" in reg.columns:
        fig_reg_stack = go.Figure()
        for gc in reg["group_code"].unique():
            rdf = reg[reg["group_code"] == gc]
            fig_reg_stack.add_trace(go.Bar(
                x=rdf["region"], y=rdf["revenue"],
                name=GROUP_NAMES.get(gc, gc),
                marker_color=BRAND.get(gc,"#999"),
            ))
        fig_reg_stack.update_layout(
            barmode="stack",
            plot_bgcolor="#f8f8f8", paper_bgcolor="#fff",
            margin=dict(l=10, r=10, t=10, b=80), height=300,
            xaxis_title="", yaxis_title="Doanh thu (VND)",
            yaxis=dict(tickformat=",.0s"),
            legend=dict(orientation="h", y=-0.3, font=dict(size=10)),
        )
    else:
        fig_reg_stack = go.Figure()

    # ─── Province scatter (n_dealers vs revenue)
    fig_scatter = px.scatter(
        prov, x="n_customers", y="revenue",
        size="n_orders", color="region",
        color_discrete_map=REGION_COLORS,
        hover_data=["province_name"],
        labels={"n_customers":"Số đại lý","revenue":"Doanh thu","region":"Vùng"},
    )
    fig_scatter.update_layout(
        plot_bgcolor="#f8f8f8", paper_bgcolor="#fff",
        margin=dict(l=10, r=10, t=10, b=40), height=300,
        yaxis=dict(tickformat=",.0s"),
        legend=dict(orientation="h", y=-0.25, font=dict(size=10)),
    )

    return html.Div([
        html.Div([
            html.H4("Phân tích địa lý — Tỉnh thành & Vùng miền"),
            html.P("74 tỉnh | 4 vùng | Jan 2025 – Mar 2026"),
        ], className="page-header", style={"background": "linear-gradient(135deg,#D85A30,#1D9E7500)"}),

        dbc.Row([
            dbc.Col(html.Div([
                html.Div("Top 20 tỉnh theo doanh thu", className="chart-title"),
                dcc.Graph(figure=fig_prov, config={"displayModeBar": False}),
            ], className="chart-card"), md=8),
            dbc.Col([
                html.Div([
                    html.Div("Tỉ trọng doanh thu theo vùng", className="chart-title"),
                    dcc.Graph(figure=fig_reg_donut, config={"displayModeBar": False}),
                ], className="chart-card"),
                html.Div([
                    html.Div("Đại lý vs Doanh thu (scatter)", className="chart-title"),
                    dcc.Graph(figure=fig_scatter, config={"displayModeBar": False}),
                ], className="chart-card"),
            ], md=4),
        ]),

        dbc.Row([
            dbc.Col(html.Div([
                html.Div("Doanh thu theo vùng × nhóm sản phẩm", className="chart-title"),
                dcc.Graph(figure=fig_reg_stack, config={"displayModeBar": False}),
            ], className="chart-card"), md=12),
        ]),

        html.Div("Xe đạp Thống Nhất • DATA EXPLORERS 2026", className="watermark"),
    ], style={"padding": "20px"})
