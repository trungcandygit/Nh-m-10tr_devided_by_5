"""
Dashboard BI — Xe đạp Thống Nhất 2025–T3/2026
Streamlit multipage: 6 màn hình theo yêu cầu đề thi

Chạy: streamlit run dashboard/app.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st

st.set_page_config(
    page_title="Thống Nhất Bike | BI Dashboard",
    page_icon="🚲",
    layout="wide",
    initial_sidebar_state="expanded",
)

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from analytics.kpi_calculator import (
    load_fact_sales, kpi_san_luong, kpi_doanh_thu,
    kpi_tang_truong, kpi_co_cau_sp, kpi_dai_ly, kpi_van_hanh,
)
from analytics.rfm_analysis        import compute_rfm, detect_churn_risk, segment_summary
from analytics.bcg_matrix          import compute_bcg
from analytics.market_basket       import build_basket, co_purchase_heatmap
from analytics.geographic_analysis import (
    revenue_by_province, revenue_by_region_quarter, geo_growth,
)
from dashboard.config import (
    COLORS, GROUP_LABELS, REGION_COLORS, SEGMENT_COLORS, BCG_COLORS,
)


@st.cache_data(ttl=300)
def _load():
    return load_fact_sales()


# ── Sidebar ─────────────────────────────────────────────────────
st.sidebar.title("🚲 Thống Nhất Bike")
st.sidebar.caption("BI Dashboard 2025–T3/2026")

man_hinh = st.sidebar.radio("Màn hình", [
    "① Tổng quan kinh doanh",
    "② Phân tích thời gian",
    "③ Phân tích sản phẩm",
    "④ Phân tích đại lý",
    "⑤ Phân tích địa lý",
    "⑥ Trạng thái vận hành",
])

try:
    df_all = _load()
    data_ok = True
except Exception as e:
    st.warning(f"Chưa kết nối được DB: {e}. Đang dùng dữ liệu mẫu.")
    data_ok = False
    df_all  = pd.DataFrame()

if data_ok and not df_all.empty:
    years = sorted(df_all["fiscal_year"].unique())
    selected_years = st.sidebar.multiselect("Năm tài chính", years, default=years)
    df = df_all[df_all["fiscal_year"].isin(selected_years)]
else:
    df = df_all


# ═══════════════════════════════════════════════════════════════
# MÀN HÌNH 1 — TỔNG QUAN
# ═══════════════════════════════════════════════════════════════
if man_hinh.startswith("①"):
    st.title("Tổng quan kinh doanh")
    st.caption("Dữ liệu: 02/01/2025 – 31/03/2026 | Nguồn: tnbike_db + Pipeline T3/2026")

    if not df.empty:
        kpi1 = kpi_san_luong(df)
        kpi2 = kpi_doanh_thu(df)
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Tổng doanh thu",    f"{kpi2['tong_doanh_thu']/1e9:.1f} tỷ")
        c2.metric("Tổng đơn hàng",     f"{kpi1['tong_don_hang']:,}")
        c3.metric("Tổng sản lượng",    f"{kpi1['tong_so_luong_ban']:,} chiếc")
        c4.metric("Đại lý hoạt động",  f"{kpi2['tong_dai_ly_hoat_dong']:,}")
        c5.metric("Giá bán TB",        f"{kpi2['gia_ban_trung_binh']/1e6:.2f} tr/chiếc")
        c6.metric("DT TB/đại lý",      f"{kpi2['doanh_thu_tb_moi_dai_ly']/1e6:.0f} tr")

        st.divider()
        col1, col2 = st.columns([2, 1])

        with col1:
            st.subheader("Doanh thu theo tháng")
            monthly = kpi_tang_truong(df)
            monthly["dt_ty"] = monthly["line_total"] / 1e9
            fig = px.line(
                monthly, x="label", y="dt_ty", markers=True,
                color_discrete_sequence=["#1D9E75"],
                labels={"dt_ty": "Doanh thu (tỷ đồng)", "label": ""},
            )
            fig.update_layout(height=300, hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("Cơ cấu nhóm SP")
            ccat = kpi_co_cau_sp(df)
            ccat["label"] = ccat["group_code"].map(GROUP_LABELS)
            fig2 = px.pie(
                ccat, values="doanh_thu", names="label",
                color="group_code", color_discrete_map=COLORS, hole=0.4,
            )
            fig2.update_layout(height=300, showlegend=True)
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()
    st.subheader("Phễu xử lý đơn hàng T3/2026 (Hạng mục A)")
    kv = kpi_van_hanh()
    if "tong_file" in kv:
        cf1, cf2, cf3, cf4 = st.columns(4)
        cf1.metric("Tổng file đầu vào", kv["tong_file"])
        cf2.metric("Thành công", kv["thanh_cong"], f"{kv['ti_le_thanh_cong']}%")
        cf3.metric("Lỗi (Invalid)",     kv["loi_invalid"])
        cf4.metric("Cảnh báo",          kv["canh_bao"])
    else:
        st.info("Pipeline chưa chạy. Chạy: python -m pipeline.run_pipeline")


# ═══════════════════════════════════════════════════════════════
# MÀN HÌNH 2 — THỜI GIAN
# ═══════════════════════════════════════════════════════════════
elif man_hinh.startswith("②"):
    st.title("Phân tích thời gian")

    if df.empty:
        st.warning("Không có dữ liệu.")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["Xu hướng doanh số", "So sánh cùng kỳ", "Mùa vụ"])

    with tab1:
        st.subheader("Doanh thu theo tháng × Nhóm sản phẩm")
        mg = df.groupby(["fiscal_year", "fiscal_month", "group_code"])["line_total"].sum().reset_index()
        mg["label"]  = mg.apply(lambda r: f"T{r.fiscal_month}/{str(r.fiscal_year)[2:]}", axis=1)
        mg["dt_ty"]  = mg["line_total"] / 1e9
        mg["group_label"] = mg["group_code"].map(GROUP_LABELS)
        fig = px.line(
            mg, x="label", y="dt_ty", color="group_code",
            color_discrete_map=COLORS, markers=True,
            labels={"dt_ty": "Doanh thu (tỷ đồng)", "label": ""},
        )
        for trace in fig.data:
            trace.name = GROUP_LABELS.get(trace.name, trace.name)
        fig.update_layout(height=420, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("So sánh Q1/2025 vs Q1/2026 theo nhóm SP")
        q1_25 = df_all[(df_all["fiscal_year"] == 2025) & (df_all["fiscal_quarter"] == 1)].groupby("group_code")["line_total"].sum().reset_index()
        q1_26 = df_all[(df_all["fiscal_year"] == 2026) & (df_all["fiscal_quarter"] == 1)].groupby("group_code")["line_total"].sum().reset_index()
        q1_25["ky"] = "Q1/2025"
        q1_26["ky"] = "Q1/2026"
        comp = pd.concat([q1_25, q1_26])
        comp["group_label"] = comp["group_code"].map(GROUP_LABELS)
        comp["dt_ty"] = comp["line_total"] / 1e9
        fig2 = px.bar(
            comp, x="group_label", y="dt_ty", color="ky", barmode="group",
            color_discrete_sequence=["#888780", "#1D9E75"],
            labels={"dt_ty": "Doanh thu (tỷ đồng)", "group_label": ""},
        )
        fig2.update_layout(height=380)
        st.plotly_chart(fig2, use_container_width=True)

        # % thay đổi
        comp_pivot = comp.pivot(index="group_label", columns="ky", values="line_total").fillna(0)
        if "Q1/2025" in comp_pivot.columns and "Q1/2026" in comp_pivot.columns:
            comp_pivot["YoY%"] = ((comp_pivot["Q1/2026"] - comp_pivot["Q1/2025"]) / comp_pivot["Q1/2025"].replace(0, 1) * 100).round(1)
            st.dataframe(comp_pivot.reset_index(), use_container_width=True)

    with tab3:
        st.subheader("Mùa vụ — DT trung bình theo tháng trong năm")
        seasonal = df_all.groupby("fiscal_month")["line_total"].mean().reset_index()
        seasonal["label"] = "Tháng " + seasonal["fiscal_month"].astype(str)
        seasonal["dt_ty"] = seasonal["line_total"] / 1e9
        fig3 = px.bar(
            seasonal, x="label", y="dt_ty",
            color="dt_ty", color_continuous_scale="Teal",
            labels={"dt_ty": "DT trung bình (tỷ đồng)", "label": ""},
        )
        fig3.update_layout(height=340, coloraxis_showscale=False)
        st.plotly_chart(fig3, use_container_width=True)
        st.info("Tháng 3 là đỉnh mùa vụ — hiệu ứng tựu trường Hè + mua sắm đầu năm học mới.")


# ═══════════════════════════════════════════════════════════════
# MÀN HÌNH 3 — SẢN PHẨM
# ═══════════════════════════════════════════════════════════════
elif man_hinh.startswith("③"):
    st.title("Phân tích sản phẩm")

    if df.empty:
        st.warning("Không có dữ liệu.")
        st.stop()

    tab1, tab2, tab3 = st.tabs(["3 cấp phân tích", "BCG Matrix", "Màu sắc & Giỏ hàng"])

    with tab1:
        level = st.radio("Cấp phân tích", ["Cấp 1: Nhóm SP", "Cấp 2: Dòng xe", "Cấp 3: SKU/Màu sắc"], horizontal=True)
        if level.startswith("Cấp 1"):
            data = df.groupby(["group_code", "group_name"]).agg(
                doanh_thu=("line_total", "sum"), so_luong=("quantity", "sum")
            ).reset_index()
            data["label"] = data["group_code"].map(GROUP_LABELS)
            data["dt_ty"] = data["doanh_thu"] / 1e9
            fig = px.bar(data, x="dt_ty", y="label", orientation="h",
                         color="group_code", color_discrete_map=COLORS,
                         labels={"dt_ty": "Doanh thu (tỷ đồng)", "label": ""})
        elif level.startswith("Cấp 2"):
            data = df.groupby("line_name").agg(
                doanh_thu=("line_total", "sum"), so_luong=("quantity", "sum")
            ).reset_index().nlargest(20, "doanh_thu")
            data["dt_ty"] = data["doanh_thu"] / 1e9
            fig = px.bar(data, x="dt_ty", y="line_name", orientation="h",
                         color_discrete_sequence=["#1D9E75"],
                         labels={"dt_ty": "Doanh thu (tỷ đồng)", "line_name": ""})
            fig.update_layout(yaxis=dict(autorange="reversed"))
        else:
            data = df.groupby(["product_name", "color"])["quantity"].sum().reset_index().nlargest(25, "quantity")
            fig = px.treemap(data, path=["color", "product_name"], values="quantity",
                             color="quantity", color_continuous_scale="Teal")
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("BCG Matrix — 5 nhóm sản phẩm")
        bcg = compute_bcg(df_all)
        if not bcg.empty:
            bcg["label"] = bcg["group_code"].map(GROUP_LABELS)
            fig_bcg = go.Figure()
            for _, row in bcg.iterrows():
                fig_bcg.add_trace(go.Scatter(
                    x=[row["market_share_pct"]], y=[row["growth_pct"]],
                    mode="markers+text",
                    marker=dict(
                        size=max(20, row["market_share_pct"] * 2.5),
                        color=BCG_COLORS.get(row["bcg_label"], "#AAA"),
                        opacity=0.85,
                    ),
                    text=[row["label"]], textposition="top center",
                    name=row["bcg_label"],
                ))
            med_x = bcg["market_share_pct"].median()
            med_y = bcg["growth_pct"].median()
            fig_bcg.add_vline(x=med_x, line_dash="dash", line_color="gray", opacity=0.5)
            fig_bcg.add_hline(y=med_y, line_dash="dash", line_color="gray", opacity=0.5)
            fig_bcg.update_layout(
                height=450,
                xaxis_title="Thị phần doanh thu (%)",
                yaxis_title="Tốc độ tăng trưởng Q1 YoY (%)",
                showlegend=False,
            )
            st.plotly_chart(fig_bcg, use_container_width=True)
            st.dataframe(
                bcg[["group_code", "label", "market_share_pct", "growth_pct", "bcg_label"]]
                .rename(columns={"label": "Nhóm SP", "market_share_pct": "Thị phần%",
                                  "growth_pct": "Tăng trưởng%", "bcg_label": "BCG"}),
                hide_index=True, use_container_width=True,
            )

    with tab3:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Heatmap màu sắc × nhóm SP")
            if "color" in df.columns:
                color_data = (
                    df[df["color"].notna() & (df["color"] != "")]
                    .groupby(["group_code", "color"])["quantity"].sum().reset_index()
                )
                color_data["group_label"] = color_data["group_code"].map(GROUP_LABELS)
                fig_col = px.density_heatmap(
                    color_data, x="group_label", y="color", z="quantity",
                    color_continuous_scale="Teal",
                    labels={"quantity": "Số lượng", "group_label": "Nhóm SP", "color": "Màu sắc"},
                )
                fig_col.update_layout(height=420)
                st.plotly_chart(fig_col, use_container_width=True)

        with col2:
            st.subheader("Đồng mua hàng (Co-purchase)")
            try:
                basket = build_basket(df, by="group_code")
                copurchase = co_purchase_heatmap(df, by="group_code")
                copurchase.columns = [GROUP_LABELS.get(c, c) for c in copurchase.columns]
                copurchase.index   = [GROUP_LABELS.get(i, i) for i in copurchase.index]
                fig_cp = px.imshow(
                    copurchase, color_continuous_scale="Blues",
                    labels={"color": "Số đơn hàng"},
                )
                fig_cp.update_layout(height=420)
                st.plotly_chart(fig_cp, use_container_width=True)
            except Exception as e:
                st.warning(f"Cần cài mlxtend: {e}")


# ═══════════════════════════════════════════════════════════════
# MÀN HÌNH 4 — ĐẠI LÝ
# ═══════════════════════════════════════════════════════════════
elif man_hinh.startswith("④"):
    st.title("Phân tích đại lý — RFM & Churn")

    if df.empty:
        st.warning("Không có dữ liệu.")
        st.stop()

    rfm   = compute_rfm(df)
    churn = detect_churn_risk(rfm)

    tab1, tab2, tab3 = st.tabs(["RFM Scatter", "Top / Bottom", "Nguy cơ rời bỏ"])

    with tab1:
        st.subheader("Phân tán RFM — 702 đại lý")
        rfm["monetary_ty"] = rfm["monetary"] / 1e9
        fig_rfm = px.scatter(
            rfm, x="freq", y="recency_days",
            size="monetary_ty", color="segment",
            color_discrete_map=SEGMENT_COLORS,
            hover_data={"customer_name": True, "monetary_ty": ":.2f"},
            labels={
                "freq": "Tần suất đặt hàng",
                "recency_days": "Recency (ngày)",
                "monetary_ty": "Doanh thu (tỷ)",
            },
            size_max=40,
        )
        fig_rfm.update_yaxes(autorange="reversed")
        fig_rfm.update_layout(height=480)
        st.plotly_chart(fig_rfm, use_container_width=True)

        seg = segment_summary(rfm)
        seg["doanh_thu"] = (seg["doanh_thu"] / 1e6).round(0).astype(int)
        seg.columns = ["Phân khúc", "Số đại lý", "DT (triệu)", "Recency TB (ngày)", "Freq TB"]
        st.dataframe(seg, hide_index=True, use_container_width=True)

    with tab2:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Top 10 doanh thu cao nhất")
            t10 = rfm.nlargest(10, "monetary")[["customer_name", "monetary", "freq", "recency_days", "segment"]].copy()
            t10["monetary"] = (t10["monetary"] / 1e6).round(0).astype(int)
            t10.columns = ["Đại lý", "DT (triệu)", "Số đơn", "Recency (ngày)", "Phân khúc"]
            st.dataframe(t10, hide_index=True, use_container_width=True)
        with c2:
            st.subheader("10 đại lý hoạt động yếu nhất")
            b10 = rfm.nsmallest(10, "monetary")[["customer_name", "monetary", "freq", "recency_days", "segment"]].copy()
            b10["monetary"] = (b10["monetary"] / 1e6).round(0).astype(int)
            b10.columns = ["Đại lý", "DT (triệu)", "Số đơn", "Recency (ngày)", "Phân khúc"]
            st.dataframe(b10, hide_index=True, use_container_width=True)

        st.divider()
        rev_sorted  = rfm["monetary"].sort_values(ascending=False)
        cumulative  = rev_sorted.cumsum() / rev_sorted.sum() * 100
        n           = len(cumulative)
        pct_80      = next((i / n * 100 for i, v in enumerate(cumulative.values) if v >= 80), 100)
        st.metric(
            "Nguyên lý Pareto",
            f"{pct_80:.0f}% đại lý tạo ra 80% doanh thu",
            delta=f"Top 5 chiếm {rfm.nlargest(5,'monetary')['monetary'].sum()/rfm['monetary'].sum()*100:.1f}%",
        )

    with tab3:
        st.subheader(f"Danh sách {len(churn)} đại lý nguy cơ rời bỏ")
        churn_d = churn[["customer_name", "recency_days", "freq", "monetary", "segment", "churn_prob"]].copy()
        churn_d["monetary"]  = (churn_d["monetary"] / 1e6).round(0).astype(int)
        churn_d["churn_prob"] = (churn_d["churn_prob"] * 100).round(1)
        churn_d.columns = ["Đại lý", "Ngày cuối mua", "Số đơn", "DT (triệu)", "Phân khúc", "Xác suất rời bỏ (%)"]
        st.dataframe(churn_d.head(40), hide_index=True, use_container_width=True)


# ═══════════════════════════════════════════════════════════════
# MÀN HÌNH 5 — ĐỊA LÝ
# ═══════════════════════════════════════════════════════════════
elif man_hinh.startswith("⑤"):
    st.title("Phân tích địa lý — 63 tỉnh thành · 3 miền")

    if df.empty:
        st.warning("Không có dữ liệu.")
        st.stop()

    by_prov   = revenue_by_province(df)
    by_region = revenue_by_region_quarter(df)

    tab1, tab2, tab3 = st.tabs(["Tỉnh thành", "Vùng miền", "Tăng trưởng"])

    with tab1:
        top_n = st.slider("Hiển thị top N tỉnh", 10, 50, 25)
        top_prov = by_prov.head(top_n).copy()
        top_prov["dt_ty"] = top_prov["doanh_thu"] / 1e9
        fig = px.bar(
            top_prov, x="dt_ty", y="province_name", orientation="h",
            color="region", color_discrete_map=REGION_COLORS,
            labels={"dt_ty": "Doanh thu (tỷ đồng)", "province_name": ""},
            height=max(400, top_n * 22),
        )
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

        by_prov2 = by_prov.copy()
        by_prov2["dt_ty"] = by_prov2["doanh_thu"] / 1e9
        fig2 = px.treemap(
            by_prov2, path=["region", "province_name"], values="dt_ty",
            color="region", color_discrete_map=REGION_COLORS,
        )
        fig2.update_layout(height=450)
        st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        st.subheader("Doanh thu 3 miền theo quý")
        by_region2 = by_region.copy()
        by_region2["q_label"] = "Q" + by_region2["fiscal_quarter"].astype(str) + "/" + by_region2["fiscal_year"].astype(str).str[-2:]
        by_region2["dt_ty"] = by_region2["line_total"] / 1e9
        fig3 = px.bar(
            by_region2, x="q_label", y="dt_ty", color="region",
            barmode="stack", color_discrete_map=REGION_COLORS,
            labels={"dt_ty": "Doanh thu (tỷ đồng)", "q_label": ""},
        )
        fig3.update_layout(height=380)
        st.plotly_chart(fig3, use_container_width=True)

    with tab3:
        st.subheader("Tăng trưởng tỉnh: Q1/2026 vs Q1/2025")
        growth = geo_growth(df_all)
        if not growth.empty:
            fig4 = px.bar(
                growth.head(30), x="growth_pct", y="province_name",
                orientation="h", color="growth_pct",
                color_continuous_scale="RdYlGn",
                labels={"growth_pct": "Tăng trưởng (%)", "province_name": ""},
            )
            fig4.update_layout(height=550, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig4, use_container_width=True)


# ═══════════════════════════════════════════════════════════════
# MÀN HÌNH 6 — VẬN HÀNH
# ═══════════════════════════════════════════════════════════════
elif man_hinh.startswith("⑥"):
    import json
    from pathlib import Path

    st.title("Trạng thái vận hành — Pipeline A")

    kv = kpi_van_hanh()
    if "tong_file" not in kv:
        st.warning("Pipeline chưa chạy. Chạy lệnh:")
        st.code("python -m pipeline.run_pipeline --email-dir data/raw/emails --pdf-dir data/raw/pdfs")
        st.stop()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("File đầu vào",      kv["tong_file"])
    c2.metric("Thành công",         kv["thanh_cong"], f"{kv['ti_le_thanh_cong']}%")
    c3.metric("Lỗi (Invalid)",      kv["loi_invalid"])
    c4.metric("Cảnh báo",           kv["canh_bao"])
    c5.metric("Thời gian TB",       f"{kv['thoi_gian_tb_giay']}s/file")

    fig_donut = go.Figure(go.Pie(
        labels=["Thành công", "Lỗi", "Cảnh báo"],
        values=[kv["thanh_cong"], kv["loi_invalid"], kv["canh_bao"]],
        hole=0.6,
        marker_colors=["#1D9E75", "#E24B4A", "#BA7517"],
    ))
    fig_donut.update_layout(height=350, title="Kết quả xử lý 1.132 đơn hàng T3/2026")
    st.plotly_chart(fig_donut, use_container_width=True)

    result_path = Path(__file__).parent.parent / "data/processed/pipeline_result.json"
    if result_path.exists():
        result = json.loads(result_path.read_text())
        errors = result.get("danh_sach_loi", [])
        if errors:
            st.subheader(f"Chi tiết {len(errors)} đơn hàng lỗi / cảnh báo")
            st.dataframe(pd.DataFrame(errors), use_container_width=True)
