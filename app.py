
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path

st.set_page_config(
    page_title="Push_Performance",
    page_icon="📲",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_PATH = Path(__file__).parent / "push_performance_final_data.csv"

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Push Datetime"] = pd.to_datetime(df["Push Datetime"], errors="coerce")
    df["Time Sort"] = pd.to_datetime(df["Time Sort"], errors="coerce")
    numeric_cols = ["Sent", "Read", "Read %", "Clicks", "CTR", "Conversions", "Conversion %", "Row Count"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    for col in df.columns:
        if col not in numeric_cols + ["Date", "Push Datetime", "Time Sort"]:
            df[col] = df[col].fillna("Unknown").astype(str)
    return df

df = load_data()

st.markdown("""
<style>
.block-container {padding-top: 1rem; padding-bottom: 1rem;}
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #ffffff 0%, #f7f9fc 100%);
    border: 1px solid rgba(49, 51, 63, 0.08);
    padding: 10px 12px;
    border-radius: 16px;
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
}
.small-note {color: #667085; font-size: 0.92rem;}
</style>
""", unsafe_allow_html=True)

st.title("Push_Performance")
st.caption("Dashboard rebuilt on the original structure. CTR is treated only as Clicks / Read using the sheet values.")

# ----------------------- helpers -----------------------
def weighted_pct(values, weights):
    values = pd.to_numeric(values, errors="coerce").fillna(0)
    weights = pd.to_numeric(weights, errors="coerce").fillna(0)
    denom = weights.sum()
    if denom == 0:
        return 0.0
    return float((values * weights).sum() / denom)

def summarize_frame(data, dims):
    base = data.groupby(dims, dropna=False, as_index=False)[["Sent", "Read", "Clicks", "Conversions", "Row Count"]].sum()
    read_map = data.groupby(dims, dropna=False).apply(lambda x: weighted_pct(x["Read %"], x["Sent"])).reset_index(name="Read %")
    ctr_map = data.groupby(dims, dropna=False).apply(lambda x: weighted_pct(x["CTR"], x["Read"])).reset_index(name="CTR %")
    conv_map = data.groupby(dims, dropna=False).apply(lambda x: weighted_pct(x["Conversion %"], x["Clicks"])).reset_index(name="Conversion %")
    out = base.merge(read_map, on=dims, how="left").merge(ctr_map, on=dims, how="left").merge(conv_map, on=dims, how="left")
    return out

def get_options(frame, column, sort_time=False):
    if column not in frame.columns:
        return []
    vals = frame[column].dropna().astype(str)
    vals = vals[vals != "nan"]
    if sort_time and "Time Sort" in frame.columns:
        temp = frame[[column, "Time Sort"]].drop_duplicates().sort_values("Time Sort")
        return temp[column].astype(str).tolist()
    return sorted(vals.unique().tolist())

def metric_format(metric):
    return "{:.1%}" if "%" in metric else "{:,.0f}"

def style_pivot_max(pivot, metric):
    if pivot.empty:
        return pivot.style
    styler = pivot.style.background_gradient(cmap="RdYlGn", axis=None)
    if "%" in metric:
        styler = styler.format("{:.1%}")
    else:
        styler = styler.format("{:,.0f}")
    return styler

def render_analysis_tab(filtered, base_dim, all_compare_dims, metric_choices):
    st.subheader(f"{base_dim} vs Other Metrics")
    c1, c2 = st.columns([1,1])
    with c1:
        compare_dim = st.selectbox(
            f"{base_dim} comparison",
            [x for x in all_compare_dims if x != base_dim],
            key=f"{base_dim}_compare"
        )
    with c2:
        metric = st.selectbox(
            f"{base_dim} metric",
            metric_choices,
            key=f"{base_dim}_metric"
        )

    comp = summarize_frame(filtered, [base_dim, compare_dim])
    comp = comp[(comp[base_dim].astype(str) != "Unknown") & (comp[compare_dim].astype(str) != "Unknown")]
    if comp.empty:
        st.warning("No data available for the selected filters.")
        return

    x1, x2 = st.columns([1.25, 1])

    with x1:
        chart_df = comp.sort_values(metric, ascending=False).head(60)
        fig = px.bar(
            chart_df,
            x=compare_dim,
            y=metric,
            color=base_dim,
            barmode="group",
            text_auto=".2s",
            title=f"{base_dim} vs {compare_dim} — {metric}"
        )
        if "%" in metric:
            fig.update_yaxes(tickformat=".1%")
        fig.update_layout(height=480, margin=dict(l=10, r=10, t=50, b=40), xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    with x2:
        best = comp.sort_values([compare_dim, metric], ascending=[True, False]).groupby(compare_dim).head(1)
        show_cols = [compare_dim, base_dim, metric, "Sent", "Read", "Clicks", "Conversions", "Read %", "CTR %", "Conversion %"]
        st.markdown(f"#### Best {base_dim} for each {compare_dim}")
        st.dataframe(best[show_cols].sort_values(metric, ascending=False), use_container_width=True, height=440)

    st.markdown("#### Conditional Formatting Matrix")
    pivot = comp.pivot_table(index=base_dim, columns=compare_dim, values=metric, aggfunc="sum", fill_value=0)
    st.dataframe(style_pivot_max(pivot, metric), use_container_width=True, height=470)

    st.download_button(
        f"Download {base_dim} vs {compare_dim}",
        pivot.to_csv().encode("utf-8"),
        file_name=f"{base_dim.lower().replace('/','_')}_vs_{compare_dim.lower().replace('/','_')}.csv",
        mime="text/csv",
        key=f"dl_{base_dim}_{compare_dim}_{metric}"
    )

# ----------------------- sidebar -----------------------
st.sidebar.header("Filters")

date_min = df["Date"].min()
date_max = df["Date"].max()
date_range = st.sidebar.date_input(
    "Date range",
    value=(date_min, date_max),
    min_value=date_min,
    max_value=date_max
)

with st.sidebar.expander("Planning filters", expanded=True):
    day_options = get_options(df, "Day")
    week_options = get_options(df, "Week")
    month_options = get_options(df, "Month")
    time_options = get_options(df, "Time Label", sort_time=True)
    day_sel = st.multiselect("Day", day_options, default=day_options)
    week_sel = st.multiselect("Week", week_options, default=week_options)
    month_sel = st.multiselect("Month", month_options, default=month_options)
    time_sel = st.multiselect("Time", time_options, default=time_options)
    campaign_sel = st.multiselect("Campaign Name", get_options(df, "Campaign Name"), default=[])

with st.sidebar.expander("Audience filters", expanded=False):
    segment_options = get_options(df, "Segment")
    affinity_options = get_options(df, "Affinity")
    affdef_options = get_options(df, "Affinity Definition")
    retailer_options = get_options(df, "Retailer")
    tgcg_options = get_options(df, "TG/CG")
    segment_sel = st.multiselect("Segment", segment_options, default=segment_options)
    affinity_sel = st.multiselect("Affinity", affinity_options, default=affinity_options)
    aff_def_sel = st.multiselect("Affinity Definition", affdef_options, default=affdef_options)
    retailer_sel = st.multiselect("Retailer", retailer_options, default=retailer_options)
    tgcg_sel = st.multiselect("TG/CG", tgcg_options, default=tgcg_options)

with st.sidebar.expander("Content filters", expanded=False):
    theme_options = get_options(df, "Theme")
    lever_options = get_options(df, "Lever")
    ctype_options = get_options(df, "Campaign Type")
    brief_options = get_options(df, "Brief")
    ab_options = get_options(df, "A/B")
    msg_a_options = get_options(df, "Message A")
    msg_b_options = get_options(df, "Message B")
    theme_sel = st.multiselect("Theme", theme_options, default=theme_options)
    lever_sel = st.multiselect("Lever", lever_options, default=lever_options)
    campaign_type_sel = st.multiselect("Campaign Type", ctype_options, default=ctype_options)
    brief_sel = st.multiselect("Brief", brief_options, default=brief_options)
    ab_sel = st.multiselect("A/B", ab_options, default=ab_options)
    msg_a_sel = st.multiselect("Message A", msg_a_options, default=msg_a_options)
    msg_b_sel = st.multiselect("Message B", msg_b_options, default=msg_b_options)

filtered = df.copy()
if len(date_range) == 2:
    start_date = pd.to_datetime(date_range[0])
    end_date = pd.to_datetime(date_range[1])
    filtered = filtered[(filtered["Date"] >= start_date) & (filtered["Date"] <= end_date)]

selection_map = {
    "Day": day_sel,
    "Week": week_sel,
    "Month": month_sel,
    "Time Label": time_sel,
    "Segment": segment_sel,
    "Affinity": affinity_sel,
    "Affinity Definition": aff_def_sel,
    "Retailer": retailer_sel,
    "TG/CG": tgcg_sel,
    "Theme": theme_sel,
    "Lever": lever_sel,
    "Campaign Type": campaign_type_sel,
    "Brief": brief_sel,
    "A/B": ab_sel,
    "Message A": msg_a_sel,
    "Message B": msg_b_sel,
}
for col, vals in selection_map.items():
    if vals:
        filtered = filtered[filtered[col].astype(str).isin(vals)]
if campaign_sel:
    filtered = filtered[filtered["Campaign Name"].astype(str).isin(campaign_sel)]

# ----------------------- metrics -----------------------
metric_choices = ["Sent", "Read", "Clicks", "Conversions", "Read %", "CTR %", "Conversion %"]
compare_dims = ["Time Label", "Theme", "Lever", "Segment", "Campaign Type", "Retailer", "Affinity", "TG/CG", "Affinity Definition"]

# ----------------------- executive summary -----------------------
total_sent = float(filtered["Sent"].sum())
total_read = float(filtered["Read"].sum())
total_clicks = float(filtered["Clicks"].sum())
total_conv = float(filtered["Conversions"].sum())
total_rows = int(filtered["Row Count"].sum())
unique_campaigns = filtered["Campaign Name"].nunique()

sheet_read = weighted_pct(filtered["Read %"], filtered["Sent"])
sheet_ctr = weighted_pct(filtered["CTR"], filtered["Read"])   # only CTR, from sheet
sheet_conv = weighted_pct(filtered["Conversion %"], filtered["Clicks"])

st.subheader("Executive Summary")
r1, r2, r3, r4, r5, r6 = st.columns(6)
r1.metric("Campaign Rows", f"{total_rows:,.0f}")
r2.metric("Unique Campaigns", f"{unique_campaigns:,.0f}")
r3.metric("Sent", f"{total_sent:,.0f}")
r4.metric("Read", f"{total_read:,.0f}")
r5.metric("Clicks", f"{total_clicks:,.0f}")
r6.metric("Conversions", f"{total_conv:,.0f}")

r7, r8, r9 = st.columns(3)
r7.metric("Read %", f"{sheet_read:.2%}")
r8.metric("CTR %", f"{sheet_ctr:.2%}")
r9.metric("Conversion %", f"{sheet_conv:.2%}")

st.markdown(
    "<div class='small-note'>Percentages use the source sheet logic. CTR is only Clicks / Read from the sheet.</div>",
    unsafe_allow_html=True
)

# ----------------------- tabs -----------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Overview",
    "Affinity Analysis",
    "Theme Analysis",
    "Lever Analysis",
    "Segment Analysis",
    "Campaign Type Analysis",
    "Detailed Table"
])

# ----------------------- overview -----------------------
with tab1:
    a1, a2 = st.columns([1.4, 1])

    with a1:
        trend_metric = st.selectbox("Daily trend metric", ["Sent", "Read", "Clicks", "Conversions"], index=2)
        trend = summarize_frame(filtered, ["Push Datetime", "Time Label"]).sort_values("Push Datetime")
        fig_trend = px.bar(
            trend,
            x="Push Datetime",
            y=trend_metric,
            color="Time Label",
            text_auto=True,
            title=f"Daily Trend by Push Delivery Time — {trend_metric}"
        )
        fig_trend.update_traces(textposition="outside", cliponaxis=False)
        fig_trend.update_layout(height=430, margin=dict(l=10, r=10, t=50, b=10), xaxis_title="")
        st.plotly_chart(fig_trend, use_container_width=True)

    with a2:
        campaign_type_metric = st.selectbox("Top Campaign Types metric", metric_choices, index=2)
        by_type = summarize_frame(filtered, ["Campaign Type"]).sort_values(campaign_type_metric, ascending=False).head(12)
        fig_type = px.bar(
            by_type,
            x="Campaign Type",
            y=campaign_type_metric,
            title=f"Top Campaign Types by {campaign_type_metric}",
            text_auto=".2s"
        )
        if "%" in campaign_type_metric:
            fig_type.update_yaxes(tickformat=".1%")
        fig_type.update_layout(height=430, margin=dict(l=10, r=10, t=50, b=40), xaxis_title="")
        st.plotly_chart(fig_type, use_container_width=True)

    b1, b2 = st.columns(2)

    with b1:
        retailer_metric = st.selectbox("Top Retailers metric", metric_choices, index=2)
        retailer = summarize_frame(filtered, ["Retailer"]).sort_values(retailer_metric, ascending=False).head(12)
        fig_retailer = px.bar(
            retailer,
            x="Retailer",
            y=retailer_metric,
            title=f"Top Retailers by {retailer_metric}",
            text_auto=".2s"
        )
        if "%" in retailer_metric:
            fig_retailer.update_yaxes(tickformat=".1%")
        fig_retailer.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=40), xaxis_title="")
        st.plotly_chart(fig_retailer, use_container_width=True)

    with b2:
        segment_metric = st.selectbox("Segment metric", metric_choices, index=2)
        seg = summarize_frame(filtered, ["Segment"]).sort_values(segment_metric, ascending=False)
        fig_seg = px.bar(
            seg,
            x="Segment",
            y=segment_metric,
            title=f"Segment Comparison by {segment_metric}",
            text_auto=".2s"
        )
        if "%" in segment_metric:
            fig_seg.update_yaxes(tickformat=".1%")
        fig_seg.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=40), xaxis_title="")
        st.plotly_chart(fig_seg, use_container_width=True)

    c1, c2 = st.columns(2)

    with c1:
        heat_metric = st.selectbox("Heatmap metric", metric_choices, index=2)
        heat = summarize_frame(filtered, ["Date Label", "Time Label"])
        date_order = filtered[["Date", "Date Label"]].drop_duplicates().sort_values("Date")["Date Label"].tolist()
        time_order = filtered[["Time Label", "Time Sort"]].drop_duplicates().sort_values("Time Sort")["Time Label"].tolist()
        pivot_heat = heat.pivot(index="Date Label", columns="Time Label", values=heat_metric).fillna(0)
        pivot_heat = pivot_heat.reindex(
            index=[d for d in date_order if d in pivot_heat.index],
            columns=[t for t in time_order if t in pivot_heat.columns]
        )
        fig_heat = px.imshow(
            pivot_heat,
            text_auto=".2s",
            aspect="auto",
            title=f"Heatmap — {heat_metric} by Date × Time"
        )
        if "%" in heat_metric:
            fig_heat.update_coloraxes(colorbar_tickformat=".1%")
        fig_heat.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_heat, use_container_width=True)

    with c2:
        top_campaigns = summarize_frame(filtered, ["Campaign Name"]).sort_values("Clicks", ascending=False).head(15)
        fig_top = px.bar(
            top_campaigns,
            x="Clicks",
            y="Campaign Name",
            orientation="h",
            title="Top Campaigns by Clicks",
            text_auto=".2s"
        )
        fig_top.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_top, use_container_width=True)

# ----------------------- analysis tabs -----------------------
with tab2:
    render_analysis_tab(filtered, "Affinity", compare_dims, metric_choices)

with tab3:
    render_analysis_tab(filtered, "Theme", compare_dims, metric_choices)

with tab4:
    render_analysis_tab(filtered, "Lever", compare_dims, metric_choices)

with tab5:
    render_analysis_tab(filtered, "Segment", compare_dims, metric_choices)

with tab6:
    render_analysis_tab(filtered, "Campaign Type", compare_dims, metric_choices)

# ----------------------- detail tab -----------------------
with tab7:
    st.subheader("Detailed Performance Table")
    detail_cols = [
        "Date", "Day", "Week", "Month", "Campaign Name", "Time Label", "Segment", "Affinity Definition",
        "TG/CG", "Affinity", "Retailer", "Brief", "Theme", "Lever", "Message A", "Message B", "A/B",
        "Campaign Type", "Sent", "Read", "Read %", "Clicks", "CTR", "Conversions", "Conversion %"
    ]
    detail_cols = [c for c in detail_cols if c in filtered.columns]
    detail = filtered[detail_cols].copy()
    st.dataframe(detail.sort_values(["Date", "Clicks"], ascending=[False, False]), use_container_width=True, height=520)

    st.download_button(
        "Download filtered detail as CSV",
        detail.to_csv(index=False).encode("utf-8"),
        file_name="push_performance_filtered_detail.csv",
        mime="text/csv"
    )
