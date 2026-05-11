"""Trang 3 — Quản lý đại lý: RFM + Churn"""
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from data_loader import DATA

RFM_COLORS = {
    "Khách hàng tiêu biểu":   "#1D9E75",
    "Khách hàng trung thành":  "#378ADD",
    "Khách hàng mới tiềm năng":"#7F77DD",
    "Cần chăm sóc đặc biệt":  "#D85A30",
    "Có nguy cơ rời bỏ":       "#BA7517",
    "Cần theo dõi":            "#aaa",
}

def layout():
    df = DATA["dealer"].copy()

    # ─── RFM Scatter (R vs M, colored by segment, size by freq)
    fig_rfm = px.scatter(
        df, x="rfm_r", y="rfm_m",
        size="n_orders_q1_2025", color="rfm_segment",
        color_discrete_map=RFM_COLORS,
        hover_data=["customer_name","province_name","region"],
        labels={"rfm_r":"Recency (R)","rfm_m":"Monetary (M)","rfm_segment":"Phân khúc"},
        title="",
    )
    fig_rfm.update_layout(
        plot_bgcolor="#f8f8f8", paper_bgcolor="#fff",
        margin=dict(l=10, r=10, t=10, b=40), height=340,
        legend=dict(orientation="h", y=-0.25, font=dict(size=10)),
        xaxis=dict(range=[0.5, 5.5], dtick=1),
        yaxis=dict(range=[0.5, 5.5], dtick=1),
    )

    # ─── Churn distribution
    churn_bins = df.groupby("churn_priority").size().reset_index(name="count")
    churn_order = {"Thấp": 0, "Trung bình": 1, "Cao": 2}
    churn_bins["order"] = churn_bins["churn_priority"].map(churn_order)
    churn_bins = churn_bins.sort_values("order")
    fig_churn = go.Figure(go.Bar(
        x=churn_bins["churn_priority"],
        y=churn_bins["count"],
        marker_color=["#1D9E75", "#BA7517", "#D85A30"],
        text=churn_bins["count"],
        textposition="outside",
    ))
    fig_churn.update_layout(
        xaxis_title="Mức độ churn", yaxis_title="Số đại lý",
        plot_bgcolor="#f8f8f8", paper_bgcolor="#fff",
        margin=dict(l=10, r=10, t=10, b=40), height=280,
        showlegend=False,
    )

    # ─── RFM Segment pie
    seg_count = df.groupby("rfm_segment").size().reset_index(name="count")
    fig_seg = go.Figure(go.Pie(
        labels=seg_count["rfm_segment"],
        values=seg_count["count"],
        hole=0.4,
        marker_colors=[RFM_COLORS.get(s,"#999") for s in seg_count["rfm_segment"]],
        textinfo="label+percent",
        hovertemplate="%{label}: %{value} đại lý<extra></extra>",
    ))
    fig_seg.update_layout(
        showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10), height=280,
        paper_bgcolor="#fff",
    )

    # ─── High-risk churn table
    high_risk = df[df["churn_prob"] >= 0.6].sort_values("churn_prob", ascending=False).head(20)
    high_risk_tbl = high_risk[["customer_code","customer_name","province_name","region",
                                "rfm_segment","churn_prob","n_orders_q1_2025","revenue_q1_2025"]].copy()
    high_risk_tbl["churn_prob"]        = high_risk_tbl["churn_prob"].map("{:.1%}".format)
    high_risk_tbl["revenue_q1_2025"]   = high_risk_tbl["revenue_q1_2025"].apply(lambda x: f"{x/1e6:.1f}M")
    high_risk_tbl.columns = ["Mã ĐL","Tên đại lý","Tỉnh","Vùng","Phân khúc","P(Churn)","Đơn Q1-25","DT Q1-25"]

    return html.Div([
        html.Div([
            html.H4("Quản lý đại lý — RFM & Dự báo Churn"),
            html.P("333 đại lý phân tích | LogisticRegression | ROC-AUC test: 0.775"),
        ], className="page-header", style={"background": "linear-gradient(135deg,#7F77DD,#1D9E7500)"}),

        dbc.Row([
            dbc.Col(html.Div([
                html.Div("RFM Scatter — Recency vs Monetary (kích thước ∝ tần suất)", className="chart-title"),
                dcc.Graph(figure=fig_rfm, config={"displayModeBar": False}),
            ], className="chart-card"), md=8),
            dbc.Col([
                html.Div([
                    html.Div("Phân bổ phân khúc RFM", className="chart-title"),
                    dcc.Graph(figure=fig_seg, config={"displayModeBar": False}),
                ], className="chart-card"),
                html.Div([
                    html.Div("Phân bổ mức độ Churn", className="chart-title"),
                    dcc.Graph(figure=fig_churn, config={"displayModeBar": False}),
                ], className="chart-card"),
            ], md=4),
        ]),

        dbc.Row([
            dbc.Col(html.Div([
                html.Div("Top 20 đại lý nguy cơ rời bỏ cao nhất (P ≥ 60%)", className="chart-title"),
                dash_table.DataTable(
                    data=high_risk_tbl.to_dict("records"),
                    columns=[{"name": c, "id": c} for c in high_risk_tbl.columns],
                    style_table={"overflowX": "auto", "fontSize": "0.8rem"},
                    style_header={"backgroundColor": "#f0f2f5", "fontWeight": "600"},
                    style_cell={"padding": "6px 10px"},
                    style_data_conditional=[
                        {"if": {"row_index": "odd"}, "backgroundColor": "#fafafa"},
                        {"if": {"filter_query": '{Phân khúc} = "Có nguy cơ rời bỏ"'},
                         "color": "#D85A30", "fontWeight": "600"},
                    ],
                    sort_action="native", page_size=10,
                ),
            ], className="chart-card")),
        ]),

        html.Div("Xe đạp Thống Nhất • DATA EXPLORERS 2026", className="watermark"),
    ], style={"padding": "20px"})
