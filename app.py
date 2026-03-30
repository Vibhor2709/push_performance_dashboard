
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(layout="wide")

df = pd.read_csv("data.csv")
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

metrics = ["Sent","Read","Clicks","Conversions","Read %","CTOR %","CTR %","Conversion %"]
dimensions = [
    "Campaign Name","Retailer","Segment","Affinity","Theme",
    "Lever","Campaign Type","TG/CG","Affinity Definition","Message A","Message B"
]

st.title("Push_Performance – Advanced BI")

# -------- Filters --------
st.sidebar.header("Filters")

date_range = st.sidebar.date_input("Date range", [df["Date"].min(), df["Date"].max()])
if len(date_range)==2:
    df = df[(df["Date"]>=pd.to_datetime(date_range[0])) & (df["Date"]<=pd.to_datetime(date_range[1]))]

for col in ["Retailer","Segment","Affinity","Theme","Lever","Campaign Type"]:
    if col in df.columns:
        vals = st.sidebar.multiselect(col, sorted(df[col].dropna().unique()))
        if vals:
            df = df[df[col].isin(vals)]

# -------- KPI --------
total = df[["Sent","Read","Clicks","Conversions"]].sum()
k1,k2,k3,k4 = st.columns(4)
k1.metric("Sent", int(total["Sent"]))
k2.metric("Read", int(total["Read"]))
k3.metric("Clicks", int(total["Clicks"]))
k4.metric("Conversions", int(total["Conversions"]))

k5,k6,k7,k8 = st.columns(4)
k5.metric("Read %", f'{(total["Read"]/total["Sent"] if total["Sent"] else 0):.2%}')
k6.metric("CTOR %", f'{(total["Clicks"]/total["Read"] if total["Read"] else 0):.2%}')
k7.metric("CTR %", f'{(total["Clicks"]/total["Sent"] if total["Sent"] else 0):.2%}')
k8.metric("Conversion %", f'{(total["Conversions"]/total["Clicks"] if total["Clicks"] else 0):.2%}')

st.divider()

# -------- FULL FLEXIBLE ANALYSIS --------
st.subheader("Flexible Cross Analysis (Power BI style)")

col1,col2,col3 = st.columns(3)

with col1:
    row_dim = st.selectbox("Rows", dimensions, index=1)

with col2:
    col_dim = st.selectbox("Columns", dimensions, index=3)

with col3:
    metric = st.selectbox("Metric", metrics, index=2)

# Aggregate
agg = df.groupby([row_dim, col_dim], as_index=False)[["Sent","Read","Clicks","Conversions","Row Count"]].sum()

# Recalculate % ALWAYS from base
agg["Read %"] = np.where(agg["Sent"]>0, agg["Read"]/agg["Sent"], 0)
agg["CTOR %"] = np.where(agg["Read"]>0, agg["Clicks"]/agg["Read"], 0)
agg["CTR %"] = np.where(agg["Sent"]>0, agg["Clicks"]/agg["Sent"], 0)
agg["Conversion %"] = np.where(agg["Clicks"]>0, agg["Conversions"]/agg["Clicks"], 0)

pivot = agg.pivot(index=row_dim, columns=col_dim, values=metric).fillna(0)

st.dataframe(pivot, use_container_width=True, height=500)

st.download_button("Download Pivot", pivot.to_csv().encode(), "pivot.csv")

st.markdown("### Top Performers")

top = agg.sort_values(metric, ascending=False).head(20)
st.dataframe(top[[row_dim,col_dim,metric,"Clicks","Conversions","CTR %","Conversion %"]], use_container_width=True)

st.markdown("### Insights")

best = agg.sort_values([row_dim, metric], ascending=[True, False]).groupby(row_dim).head(1)
st.dataframe(best[[row_dim,col_dim,metric]], use_container_width=True)
