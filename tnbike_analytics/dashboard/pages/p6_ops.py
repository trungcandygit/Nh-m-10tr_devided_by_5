"""Trang 6 — Vận hành Pipeline email T3/2026"""
import dash_bootstrap_components as dbc
from dash import html, dcc
import plotly.graph_objects as go
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from data_loader import DATA

def layout():
    pipe = DATA["ops_pipeline"].copy()
    daily = DATA["ops_daily"].copy()

    # ─── Pipeline stats cards
    def stat_val(metric):
        row = pipe[pipe["metric"] == metric]
        return float(row["value"].iloc[0]) if not row.empty else 0

    total = stat_val("total_emails")
    ok    = stat_val("ok_emails")
    err   = stat_val("error_emails")
    rate  = stat_val("success_rate_pct")
    lines = stat_val("total_order_lines")
    rev   = stat_val("total_revenue")

    kpi_row = dbc.Row([
        dbc.Col(html.Div([
            html.Div("TỔNG EMAIL", className="kpi-label"),
            html.Div(f"{int(total):,}", className="kpi-value"),
            html.Div("file .eml T3/2026", className="kpi-sub"),
        ], className="kpi-card"), md=2),
        dbc.Col(html.Div([
            html.Div("XỬ LÝ THÀNH CÔNG", className="kpi-label"),
            html.Div(f"{int(ok):,}", className="kpi-value"),
            html.Div(f"Tỷ lệ {rate:.1f}%", className="kpi-sub kpi-up"),
        ], className="kpi-card", style={"borderLeftColor": "#1D9E75"}), md=2),
        dbc.Col(html.Div([
            html.Div("LỖI PARSE", className="kpi-label"),
            html.Div(f"{int(err):,}", className="kpi-value"),
            html.Div(f"{(err/total*100) if total else 0:.1f}% tổng", className="kpi-sub kpi-down"),
        ], className="kpi-card", style={"borderLeftColor": "#D85A30"}), md=2),
        dbc.Col(html.Div([
            html.Div("DÒNG ORDER LINE", className="kpi-label"),
            html.Div(f"{int(lines):,}", className="kpi-value"),
            html.Div("từ T3/2026", className="kpi-sub"),
        ], className="kpi-card", style={"borderLeftColor": "#378ADD"}), md=3),
        dbc.Col(html.Div([
            html.Div("DOANH THU T3/2026", className="kpi-label"),
            html.Div(f"{rev/1e9:.1f} tỷ", className="kpi-value"),
            html.Div("từ email pipeline", className="kpi-sub"),
        ], className="kpi-card", style={"borderLeftColor": "#7F77DD"}), md=3),
    ])

    # ─── Daily order count in March
    if not daily.empty and "order_date" in daily.columns:
        daily["order_date"] = pd.to_datetime(daily["order_date"])
        daily_srt = daily.sort_values("order_date")
        fig_daily_orders = go.Figure(go.Bar(
            x=daily_srt["order_date"],
            y=daily_srt["n_orders"],
            marker_color="#378ADD",
            hovertemplate="<b>%{x|%d/%m/%Y}</b><br>Đơn: %{y}<extra></extra>",
        ))
        fig_daily_orders.update_layout(
            xaxis_title="Ngày", yaxis_title="Số đơn hàng",
            plot_bgcolor="#f8f8f8", paper_bgcolor="#fff",
            margin=dict(l=10, r=10, t=10, b=40), height=280,
        )
        fig_daily_rev = go.Figure(go.Bar(
            x=daily_srt["order_date"],
            y=daily_srt["revenue"] / 1e9,
            marker_color="#1D9E75",
            hovertemplate="<b>%{x|%d/%m/%Y}</b><br>Doanh thu: %{y:.2f} tỷ<extra></extra>",
        ))
        fig_daily_rev.update_layout(
            xaxis_title="Ngày", yaxis_title="Doanh thu (tỷ VND)",
            plot_bgcolor="#f8f8f8", paper_bgcolor="#fff",
            margin=dict(l=10, r=10, t=10, b=40), height=280,
        )
    else:
        fig_daily_orders = go.Figure()
        fig_daily_rev    = go.Figure()

    # ─── Pipeline breakdown table
    pipe_tbl = pipe[["metric","value","note"]].copy() if "note" in pipe.columns else pipe[["metric","value"]].copy()
    pipe_tbl.columns = [c.capitalize() for c in pipe_tbl.columns]

    return html.Div([
        html.Div([
            html.H4("Vận hành Pipeline — Xử lý Email T3/2026"),
            html.P("1.132 file .eml | pdftotext | không cần PostgreSQL"),
        ], className="page-header", style={"background": "linear-gradient(135deg,#378ADD,#1D9E7500)"}),

        kpi_row,

        dbc.Row([
            dbc.Col(html.Div([
                html.Div("Số đơn hàng mỗi ngày — Tháng 3/2026", className="chart-title"),
                dcc.Graph(figure=fig_daily_orders, config={"displayModeBar": False}),
            ], className="chart-card"), md=6),
            dbc.Col(html.Div([
                html.Div("Doanh thu mỗi ngày — Tháng 3/2026", className="chart-title"),
                dcc.Graph(figure=fig_daily_rev, config={"displayModeBar": False}),
            ], className="chart-card"), md=6),
        ]),

        dbc.Row([
            dbc.Col(html.Div([
                html.Div("Thống kê pipeline", className="chart-title"),
                dbc.Table.from_dataframe(pipe_tbl, striped=True, bordered=False,
                                          hover=True, size="sm"),
            ], className="chart-card"), md=6),
        ]),

        html.Div("Xe đạp Thống Nhất • DATA EXPLORERS 2026", className="watermark"),
    ], style={"padding": "20px"})
