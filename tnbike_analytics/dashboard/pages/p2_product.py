"""Trang 2 — Phân tích sản phẩm: Pareto, BCG, màu sắc"""
import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, dash_table
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from data_loader import DATA, BRAND, GROUP_NAMES

BCG_COLORS = {
    "Star":          "#1D9E75",
    "Cash Cow":      "#378ADD",
    "Question Mark": "#BA7517",
    "Dog":           "#D85A30",
}

def layout():
    sku = DATA["sku"].copy()
    color_df = DATA["color"].copy()

    # ─── Pareto
    sku_srt = sku.sort_values("revenue", ascending=False).reset_index(drop=True)
    sku_srt["cum_pct"] = sku_srt["revenue"].cumsum() / sku_srt["revenue"].sum() * 100
    sku_srt["rank"] = sku_srt.index + 1
    fig_pareto = go.Figure()
    fig_pareto.add_trace(go.Bar(
        x=sku_srt["rank"], y=sku_srt["revenue"],
        marker_color=[BRAND.get(g,"#999") for g in sku_srt["group_code"]],
        name="Doanh thu", hovertemplate="<b>%{text}</b><br>DT: %{y:,.0f}<extra></extra>",
        text=sku_srt["product_code"],
    ))
    fig_pareto.add_trace(go.Scatter(
        x=sku_srt["rank"], y=sku_srt["cum_pct"],
        mode="lines", name="Lũy kế %",
        line=dict(color="#D85A30", width=2),
        yaxis="y2",
    ))
    fig_pareto.add_hline(y=80, line_dash="dash", line_color="#999", annotation_text="80%",
                          annotation_position="right", yref="y2")
    fig_pareto.update_layout(
        yaxis=dict(title="Doanh thu (VND)", tickformat=",.0s"),
        yaxis2=dict(title="Lũy kế %", overlaying="y", side="right", range=[0,105]),
        plot_bgcolor="#f8f8f8", paper_bgcolor="#fff",
        margin=dict(l=10, r=60, t=10, b=40), height=320,
        legend=dict(orientation="h", y=-0.2),
        xaxis_title="Thứ hạng SKU",
    )

    # ─── BCG Bubble
    bcg_df = sku[sku["bcg_quadrant"].notna()].copy()
    # normalize revenue for bubble size
    bcg_df["bubble_size"] = (bcg_df["revenue"] / bcg_df["revenue"].max() * 40 + 5).clip(5, 45)
    fig_bcg = go.Figure()
    for quad, qdf in bcg_df.groupby("bcg_quadrant"):
        fig_bcg.add_trace(go.Scatter(
            x=qdf["rev_share_in_group_pct"],
            y=qdf["yoy_rev_pct"].fillna(0),
            mode="markers",
            name=quad,
            marker=dict(
                size=qdf["bubble_size"],
                color=BCG_COLORS.get(quad, "#999"),
                opacity=0.75,
                line=dict(width=1, color="#fff"),
            ),
            text=qdf["product_code"],
            hovertemplate="<b>%{text}</b><br>Share trong nhóm: %{x:.1f}%<br>YoY: %{y:.1f}%<extra></extra>",
        ))
    fig_bcg.add_hline(y=0, line_dash="dash", line_color="#ccc")
    fig_bcg.add_vline(x=bcg_df["rev_share_in_group_pct"].median(), line_dash="dash", line_color="#ccc")
    fig_bcg.update_layout(
        xaxis_title="Thị phần trong nhóm (%)",
        yaxis_title="Tăng trưởng YoY (%)",
        plot_bgcolor="#f8f8f8", paper_bgcolor="#fff",
        margin=dict(l=10, r=10, t=10, b=40), height=360,
        legend=dict(orientation="h", y=-0.2),
    )

    # ─── Color mix heatmap (nhóm × màu)
    if "color" in color_df.columns and "group_code" in color_df.columns and "revenue" in color_df.columns:
        color_heat = color_df.groupby(["group_code","color"])["revenue"].sum().reset_index()
        pivot = color_heat.pivot(index="group_code", columns="color", values="revenue").fillna(0)
        pivot.index = [GROUP_NAMES.get(g, g) for g in pivot.index]
        fig_color = go.Figure(go.Heatmap(
            z=pivot.values / 1e9,
            x=pivot.columns.tolist(),
            y=pivot.index.tolist(),
            colorscale="Greens",
            hovertemplate="Nhóm: %{y}<br>Màu: %{x}<br>Doanh thu: %{z:.2f} tỷ<extra></extra>",
        ))
        fig_color.update_layout(
            xaxis_title="Màu sắc", yaxis_title="",
            plot_bgcolor="#f8f8f8", paper_bgcolor="#fff",
            margin=dict(l=10, r=10, t=10, b=60), height=300,
        )
    else:
        fig_color = go.Figure()

    # ─── Top 15 SKU table
    top15 = sku_srt.head(15)[["rank","product_code","product_name","group_name",
                                "pareto_class","revenue","yoy_rev_pct","bcg_quadrant"]].copy()
    top15["revenue"] = top15["revenue"].apply(lambda x: f"{x/1e6:.0f}M")
    top15.columns = ["#","Mã SP","Tên SP","Nhóm","Pareto","DT (VND)","YoY %","BCG"]

    return html.Div([
        html.Div([
            html.H4("Phân tích sản phẩm — SKU, Pareto, BCG"),
            html.P("161 SKU hoạt động | Pareto A/B/C | BCG Matrix"),
        ], className="page-header", style={"background": "linear-gradient(135deg,#378ADD,#1D9E7500)"}),

        dbc.Row([
            dbc.Col(html.Div([
                html.Div("Biểu đồ Pareto — SKU theo doanh thu", className="chart-title"),
                dcc.Graph(figure=fig_pareto, config={"displayModeBar": False}),
            ], className="chart-card"), md=8),
            dbc.Col(html.Div([
                html.Div("Heatmap doanh thu theo Nhóm × Màu sắc", className="chart-title"),
                dcc.Graph(figure=fig_color, config={"displayModeBar": False}),
            ], className="chart-card"), md=4),
        ]),

        dbc.Row([
            dbc.Col(html.Div([
                html.Div("BCG Matrix — Bubble chart (kích thước ∝ doanh thu)", className="chart-title"),
                dcc.Graph(figure=fig_bcg, config={"displayModeBar": False}),
            ], className="chart-card"), md=6),
            dbc.Col(html.Div([
                html.Div("Top 15 SKU theo doanh thu", className="chart-title"),
                dash_table.DataTable(
                    data=top15.to_dict("records"),
                    columns=[{"name": c, "id": c} for c in top15.columns],
                    style_table={"overflowX": "auto", "fontSize": "0.8rem"},
                    style_header={"backgroundColor": "#f0f2f5", "fontWeight": "600"},
                    style_cell={"padding": "6px 10px", "textAlign": "left"},
                    style_data_conditional=[
                        {"if": {"filter_query": '{Pareto} = "A"'}, "color": "#1D9E75", "fontWeight": "600"},
                        {"if": {"row_index": "odd"}, "backgroundColor": "#fafafa"},
                    ],
                    page_size=15,
                ),
            ], className="chart-card"), md=6),
        ]),

        html.Div("Xe đạp Thống Nhất • DATA EXPLORERS 2026", className="watermark"),
    ], style={"padding": "20px"})