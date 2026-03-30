
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(layout="wide")

df = pd.read_csv("push_performance_final_data.csv")
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

def weighted_pct(values, weights):
    denom = weights.sum()
    return (values * weights).sum() / denom if denom else 0

st.title("Push_Performance")

# KPIs
sent = df["Sent"].sum()
read = df["Read"].sum()
clicks = df["Clicks"].sum()
conv = df["Conversions"].sum()

read_pct = weighted_pct(df["Read %"], df["Sent"])
ctr_pct = weighted_pct(df["CTR"], df["Read"])   # AS PER SHEET
conv_pct = weighted_pct(df["Conversion %"], df["Clicks"])

c1,c2,c3,c4 = st.columns(4)
c1.metric("Sent", int(sent))
c2.metric("Read", int(read))
c3.metric("Clicks", int(clicks))
c4.metric("Conversions", int(conv))

c5,c6,c7 = st.columns(3)
c5.metric("Read %", f"{read_pct:.2%}")
c6.metric("CTR %", f"{ctr_pct:.2%}")
c7.metric("Conversion %", f"{conv_pct:.2%}")

st.divider()

# MATRIX
row = st.selectbox("Rows", ["Affinity","Theme","Lever","Segment","Campaign Type","Retailer"])
col = st.selectbox("Columns", ["Time Label","Theme","Lever","Segment","Campaign Type","Retailer"])
metric = st.selectbox("Metric", ["Clicks","Conversions","Read %","CTR","Conversion %"])

grp = df.groupby([row,col]).agg({
    "Sent":"sum","Read":"sum","Clicks":"sum","Conversions":"sum"
}).reset_index()

grp["Read %"] = grp["Read"]/grp["Sent"]
grp["CTR"] = grp["Clicks"]/grp["Read"]
grp["Conversion %"] = grp["Conversions"]/grp["Clicks"]

pivot = grp.pivot(index=row, columns=col, values=metric).fillna(0)

if "%" in metric:
    st.dataframe(pivot.style.background_gradient(cmap="RdYlGn").format("{:.1%}"))
else:
    st.dataframe(pivot.style.background_gradient(cmap="RdYlGn"))

st.download_button("Download", pivot.to_csv().encode(), "matrix.csv")
