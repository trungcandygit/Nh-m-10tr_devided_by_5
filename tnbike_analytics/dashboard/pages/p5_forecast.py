"""Trang 5 — Dự báo: Prophet Q2/2026 + Color share + Dealer activity"""
import dash_bootstrap_components as dbc
from dash import html, dcc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from data_loader import DATA, BRAND, GROUP_NAMES

def layout():
    fmonth = DATA["fcst_monthly"].copy()
    fmonth["ds"] = pd.to_datetime(fmonth["ym"] + "-01")

    color_fcst = DATA["color_fcst"].copy()
    dealer_act = DATA["dealer_activity"].copy()

    # ─── Forecast monthly bands per group
    groups = fmonth["group_code"].dropna().unique()
    fig_fcst = go.Figure()
    for gc in groups:
        gdf = fmonth[fmonth["group_code"] == gc].sort_values("ds")
        color = BRAND.get(gc, "#999")
        hist = gdf[gdf["split"].isin(["train", "test"])]
        fcst = gdf[gdf["split"] == "forecast"]
        if not hist.empty:
            fig_fcst.add_trace(go.Scatter(
                x=hist["ds"], y=hist["y_actual"],
                mode="lines", name=GROUP_NAMES.get(gc, gc),
                line=dict(color=color, width=2.5),
                legendgroup=gc,
            ))
        if not fcst.empty:
            fig_fcst.add_trace(go.Scatter(
                x=pd.concat([fcst["ds"], fcst["ds"][::-1]]),
                y=pd.concat([fcst["yhat_upper"], fcst["yhat_lower"][::-1]]),
                fill="toself",
                fillcolor=f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.15)" if color.startswith("#") and len(color)==7 else "rgba(100,100,100,0.15)",
                line=dict(color="rgba(255,255,255,0)"),
                showlegend=False, legendgroup=gc,
                hoverinfo="skip",
            ))
            fig_fcst.add_trace(go.Scatter(
                x=fcst["ds"], y=fcst["yhat"],
                mode="lines", name=f"{GROUP_NAMES.get(gc,gc)} (dự báo)",
                line=dict(color=color, width=2, dash="dot"),
                legendgroup=gc, showlegend=False,
            ))
    fig_fcst.add_vline(x=pd.Timestamp("2026-03-01").timestamp() * 1000,
                        line_dash="dash", line_color="#D85A30",
                        annotation_text="T3/2026", annotation_position="top left")
    fig_fcst.update_layout(
        xaxis_title="", yaxis_title="Doanh thu (VND)",
        plot_bgcolor="#f8f8f8", paper_bgcolor="#fff",
        margin=dict(l=10, r=10, t=10, b=40), height=360,
        yaxis=dict(tickformat=",.0s"),
        legend=dict(orientation="h", y=-0.22, font=dict(size=10)),
    )

    # ─── Color share Q2 forecast
    if not color_fcst.empty and "color" in color_fcst.columns and "predicted_revenue" in color_fcst.columns:
        color_agg = color_fcst.groupby("color")["predicted_revenue"].sum().reset_index()
        color_agg.columns = ["color", "yhat"]
        color_agg = color_agg[color_agg["color"].str.len() > 0].nlargest(10, "yhat")
        fig_color = go.Figure(go.Bar(
            x=color_agg["yhat"],
            y=color_agg["color"],
            orientation="h",
            marker_color="#7F77DD",
            text=color_agg["yhat"].apply(lambda x: f"{x/1e9:.2f}B"),
            textposition="outside",
        ))
        fig_color.update_layout(
            xaxis_title="Doanh thu dự báo Q2 (VND)", yaxis=dict(autorange="reversed"),
            plot_bgcolor="#f8f8f8", paper_bgcolor="#fff",
            margin=dict(l=80, r=60, t=10, b=40), height=320,
            showlegend=False, xaxis=dict(tickformat=",.0s"),
        )
    else:
        fig_color = go.Figure()

    # ─── Dealer activity probability histogram
    if "prob_active_30d" in dealer_act.columns:
        fig_dealer = go.Figure(go.Histogram(
            x=dealer_act["prob_active_30d"],
            nbinsx=20,
            marker_color="#378ADD",
            opacity=0.8,
        ))
        fig_dealer.add_vline(x=0.3, line_dash="dash", line_color="#D85A30",
                              annotation_text="Nguy cơ cao", annotation_position="top right")
        fig_dealer.update_layout(
            xaxis_title="Xác suất hoạt động 30 ngày tới",
            yaxis_title="Số đại lý",
            plot_bgcolor="#f8f8f8", paper_bgcolor="#fff",
            margin=dict(l=10, r=10, t=10, b=40), height=280,
        )
    else:
        fig_dealer = go.Figure()

    # ─── Priority contact table
    priority = dealer_act[dealer_act.get("priority_contact", pd.Series(0)) == 1].head(15) if "priority_contact" in dealer_act.columns else pd.DataFrame()
    if not priority.empty:
        priority_tbl = priority[["customer_code","customer_name","province_name",
                                  "region","prob_active_30d","activity_risk","recency_days"]].copy()
        priority_tbl["prob_active_30d"] = priority_tbl["prob_active_30d"].map("{:.1%}".format)
        priority_tbl.columns = ["Mã ĐL","Tên đại lý","Tỉnh","Vùng","P(Hoạt động)","Rủi ro","Ngày không đặt"]
    else:
        priority_tbl = pd.DataFrame(columns=["Mã ĐL","Tên đại lý","Tỉnh","Vùng","P(Hoạt động)","Rủi ro","Ngày không đặt"])

    return html.Div([
        html.Div([
            html.H4("Dự báo Q2/2026 — Prophet + Dealer Activity"),
            html.P("Forecast: Apr–Jun 2026 | Backtest: Mar 2026 | Model: Prophet (logistic growth)"),
        ], className="page-header", style={"background": "linear-gradient(135deg,#BA7517,#1D9E7500)"}),

        dbc.Row([
            dbc.Col(html.Div([
                html.Div("Dự báo doanh thu Q2/2026 theo nhóm sản phẩm (Prophet)", className="chart-title"),
                dcc.Graph(figure=fig_fcst, config={"displayModeBar": False}),
            ], className="chart-card"), md=12),
        ]),

        dbc.Row([
            dbc.Col(html.Div([
                html.Div("Dự báo doanh thu Q2 theo màu sắc (Top 10)", className="chart-title"),
                dcc.Graph(figure=fig_color, config={"displayModeBar": False}),
            ], className="chart-card"), md=6),
            dbc.Col(html.Div([
                html.Div("Phân bố xác suất đại lý hoạt động 30 ngày tới", className="chart-title"),
                dcc.Graph(figure=fig_dealer, config={"displayModeBar": False}),
            ], className="chart-card"), md=6),
        ]),

        dbc.Row([
            dbc.Col(html.Div([
                html.Div("Đại lý cần liên hệ ưu tiên (P(hoạt động) < 30%)", className="chart-title"),
                dbc.Table.from_dataframe(priority_tbl, striped=True, bordered=False,
                                          hover=True, size="sm",
                                          className="mb-0") if not priority_tbl.empty else html.P("Không có đại lý nào"),
            ], className="chart-card")),
        ]),

        html.Div("Xe đạp Thống Nhất • DATA EXPLORERS 2026", className="watermark"),
    ], style={"padding": "20px"})
