
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

DATA_PATH = Path(__file__).parent / "push_numbers_march_clean.csv"

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    numeric_cols = ["Sent", "Read", "Read_Pct", "Clicks", "CTR", "Conversions", "Conversion_Pct"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    for col in df.columns:
        if col not in numeric_cols + ["Date"]:
            df[col] = df[col].fillna("Unknown").astype(str)
    df["Month_Sort"] = df["Date"].dt.month
    return df

df = load_data()

st.markdown("""
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 1rem;}
[data-testid="stMetricValue"] {font-size: 1.8rem;}
.kpi-card {
    background: linear-gradient(135deg, #ffffff 0%, #f7f9fc 100%);
    border: 1px solid rgba(49, 51, 63, 0.08);
    padding: 16px 18px;
    border-radius: 18px;
    box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
}
.title-wrap {
    padding: 8px 0 10px 0;
}
.small-note {
    color: #667085;
    font-size: 0.92rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title-wrap">', unsafe_allow_html=True)
st.title("Push_Performance")
st.caption("Interactive BI-style dashboard for push campaign planning and performance analysis.")
st.markdown('</div>', unsafe_allow_html=True)

# Sidebar filters
st.sidebar.header("Filters")

def multiselect_all(label, options, default_all=True):
    options = [x for x in options if str(x) != "nan"]
    default = options if default_all else None
    return st.sidebar.multiselect(label, options, default=default)

min_date = df["Date"].min()
max_date = df["Date"].max()
date_range = st.sidebar.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)

months = multiselect_all("Month", sorted(df["Month"].dropna().unique(), key=lambda x: str(x)))
weeks = multiselect_all("Week", sorted(df["Week"].dropna().unique()))
days = multiselect_all("Day", sorted(df["Day"].dropna().unique()))
segments = multiselect_all("Segment", sorted(df["Segment"].dropna().unique()))
tgcg = multiselect_all("TG/CG", sorted(df["TG_CG"].dropna().unique()))
campaign_types = multiselect_all("Campaign Type", sorted(df["Campaign_Type"].dropna().unique()))
retailers = multiselect_all("Retailer", sorted(df["Retailer"].dropna().unique()))
themes = multiselect_all("Theme", sorted(df["Theme"].dropna().unique()))
levers = multiselect_all("Lever", sorted(df["Lever"].dropna().unique()))
ab = multiselect_all("A/B", sorted(df["A_B"].dropna().unique()))

filtered = df.copy()

if len(date_range) == 2:
    start_date = pd.to_datetime(date_range[0])
    end_date = pd.to_datetime(date_range[1])
    filtered = filtered[(filtered["Date"] >= start_date) & (filtered["Date"] <= end_date)]

filter_map = {
    "Month": months,
    "Week": weeks,
    "Day": days,
    "Segment": segments,
    "TG_CG": tgcg,
    "Campaign_Type": campaign_types,
    "Retailer": retailers,
    "Theme": themes,
    "Lever": levers,
    "A_B": ab
}
for col, vals in filter_map.items():
    if vals:
        filtered = filtered[filtered[col].isin(vals)]

# KPI calculations
total_sent = float(filtered["Sent"].sum())
total_read = float(filtered["Read"].sum())
total_clicks = float(filtered["Clicks"].sum())
total_conv = float(filtered["Conversions"].sum())

read_rate = (total_read / total_sent) if total_sent else 0
ctr = (total_clicks / total_sent) if total_sent else 0
ctor = (total_clicks / total_read) if total_read else 0
conversion_rate = (total_conv / total_clicks) if total_clicks else 0

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Sent", f"{total_sent:,.0f}")
k2.metric("Read", f"{total_read:,.0f}")
k3.metric("Clicks", f"{total_clicks:,.0f}")
k4.metric("Conversions", f"{total_conv:,.0f}")
k5.metric("Read Rate", f"{read_rate:.2%}")
k6.metric("CTR", f"{ctr:.2%}")

l1, l2 = st.columns([1.4, 1])

with l1:
    daily = (
        filtered.groupby("Date", as_index=False)[["Sent", "Read", "Clicks", "Conversions"]]
        .sum()
        .sort_values("Date")
    )
    fig_daily = px.line(
        daily,
        x="Date",
        y=["Sent", "Read", "Clicks", "Conversions"],
        markers=True,
        title="Daily Trend",
    )
    fig_daily.update_layout(
        legend_title_text="Metric",
        height=420,
        margin=dict(l=10, r=10, t=50, b=10)
    )
    st.plotly_chart(fig_daily, use_container_width=True)

with l2:
    metric_choice = st.selectbox(
        "Compare performance by",
        ["Sent", "Read", "Clicks", "Conversions", "CTR", "Read_Pct", "Conversion_Pct"],
        index=2
    )
    by_campaign = (
        filtered.groupby("Campaign_Type", as_index=False)[metric_choice]
        .sum()
        .sort_values(metric_choice, ascending=True)
        .tail(10)
    )
    fig_campaign = px.bar(
        by_campaign,
        x=metric_choice,
        y="Campaign_Type",
        orientation="h",
        title=f"Top Campaign Types by {metric_choice.replace('_', ' ')}",
        text_auto=".2s"
    )
    fig_campaign.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig_campaign, use_container_width=True)

m1, m2 = st.columns([1, 1])

with m1:
    retailer_metric = st.selectbox("Retailer metric", ["Sent", "Read", "Clicks", "Conversions"], index=2)
    retailer_perf = (
        filtered.groupby("Retailer", as_index=False)[retailer_metric]
        .sum()
        .sort_values(retailer_metric, ascending=False)
        .head(12)
    )
    fig_retailer = px.bar(
        retailer_perf,
        x="Retailer",
        y=retailer_metric,
        title=f"Top Retailers by {retailer_metric}",
        text_auto=".2s"
    )
    fig_retailer.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=40), xaxis_title="")
    st.plotly_chart(fig_retailer, use_container_width=True)

with m2:
    segment_perf = (
        filtered.groupby("Segment", as_index=False)[["Sent", "Read", "Clicks", "Conversions"]]
        .sum()
    )
    segment_perf["CTR"] = np.where(segment_perf["Sent"] > 0, segment_perf["Clicks"] / segment_perf["Sent"], 0)
    fig_seg = px.scatter(
        segment_perf,
        x="Sent",
        y="CTR",
        size="Conversions",
        hover_name="Segment",
        title="Segment Efficiency Map",
        size_max=60
    )
    fig_seg.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig_seg, use_container_width=True)

n1, n2 = st.columns([1, 1])

with n1:
    heat = (
        filtered.groupby(["Month", "Week"], as_index=False)["Clicks"]
        .sum()
    )
    if not heat.empty:
        month_order = (
            filtered[["Month", "Month_Sort"]]
            .drop_duplicates()
            .sort_values("Month_Sort")["Month"]
            .tolist()
        )
        pivot = heat.pivot(index="Week", columns="Month", values="Clicks").fillna(0)
        pivot = pivot[[m for m in month_order if m in pivot.columns]]
        fig_heat = px.imshow(
            pivot,
            text_auto=True,
            aspect="auto",
            title="Clicks Heatmap by Month and Week"
        )
        fig_heat.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig_heat, use_container_width=True)

with n2:
    top_campaigns = (
        filtered.groupby("Campaign_Name", as_index=False)[["Sent", "Read", "Clicks", "Conversions"]]
        .sum()
    )
    top_campaigns["CTR"] = np.where(top_campaigns["Sent"] > 0, top_campaigns["Clicks"] / top_campaigns["Sent"], 0)
    top_campaigns = top_campaigns.sort_values("Clicks", ascending=False).head(12)
    fig_top = px.bar(
        top_campaigns,
        x="Clicks",
        y="Campaign_Name",
        orientation="h",
        title="Top Campaigns by Clicks",
        text_auto=".2s"
    )
    fig_top.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig_top, use_container_width=True)

st.subheader("Detailed Performance Table")

detail = (
    filtered.groupby(
        ["Date", "Month", "Week", "Campaign_Name", "Retailer", "Segment", "TG_CG", "Theme", "Lever", "Campaign_Type"],
        as_index=False
    )[["Sent", "Read", "Clicks", "Conversions"]]
    .sum()
)
detail["Read Rate"] = np.where(detail["Sent"] > 0, detail["Read"] / detail["Sent"], 0)
detail["CTR"] = np.where(detail["Sent"] > 0, detail["Clicks"] / detail["Sent"], 0)
detail["Conversion Rate"] = np.where(detail["Clicks"] > 0, detail["Conversions"] / detail["Clicks"], 0)

st.dataframe(
    detail.sort_values(["Date", "Clicks"], ascending=[False, False]),
    use_container_width=True,
    height=420
)

csv = detail.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download filtered table as CSV",
    data=csv,
    file_name="push_performance_filtered.csv",
    mime="text/csv"
)

st.markdown(
    "<div class='small-note'>Tip: deploy this app on Streamlit Community Cloud, Render, or an internal server to share a live link with your team.</div>",
    unsafe_allow_html=True
)
