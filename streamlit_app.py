import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Dow 30 Shareholder Analysis",
    page_icon=None,
    layout="wide",
)

DATA_DIR = Path(__file__).parent / "data"


@st.cache_data
def load_data() -> pd.DataFrame:
    companies = json.loads((DATA_DIR / "companies.json").read_text())
    tsr = json.loads((DATA_DIR / "tsr.json").read_text())
    dc = json.loads((DATA_DIR / "dividend_capacity.json").read_text())

    df_co = pd.DataFrame(companies)
    df_tsr = pd.DataFrame(tsr)
    df_dc = pd.DataFrame(dc)

    df = df_co.merge(df_tsr, on="ticker").merge(df_dc, on="ticker")
    df["label"] = df["name"] + " (" + df["ticker"] + ")"
    df["data_as_of"] = pd.to_datetime(df["data_as_of"])
    return df


df = load_data()

# --- Sidebar ---
st.sidebar.header("Filters")

sectors = sorted(df["sector"].unique())
selected_sectors = st.sidebar.multiselect(
    "Filter by sector",
    options=sectors,
    default=sectors,
)

st.sidebar.header("Company Deep Dive")
company_options = sorted(df["label"].tolist())
selected_label = st.sidebar.selectbox("Select company", options=company_options)

# Apply sector filter to charts
filtered = df[df["sector"].isin(selected_sectors)] if selected_sectors else df

# =============================================================================
# 1. HEADER
# =============================================================================
st.title("Dow 30 Shareholder Analysis")
st.markdown(
    "ACCA Advanced Financial Management (AFM/P4) methodology applied to all 30 "
    "Dow Jones Industrial Average constituents."
)

st.info(
    "Data sourced from company annual reports via Financial Modeling Prep. "
    "Figures represent each company's most recently completed fiscal year. "
    "This is a static historical analysis, not live data."
)

date_min = df["data_as_of"].min().strftime("%d %b %Y")
date_max = df["data_as_of"].max().strftime("%d %b %Y")
st.caption(f"Fiscal year end dates range from {date_min} to {date_max}.")

st.divider()

# =============================================================================
# 2. OVERVIEW
# =============================================================================
st.header("Overview")

avg_tsr = df["tsr"].mean()
positive_tsr = (df["tsr"] > 0).sum()
median_cap = df["dividend_capacity"].median()
median_adj = df["adjusted_dividend_capacity"].median()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Average TSR", f"{avg_tsr:.2f}%")
col2.metric("Companies with positive TSR", f"{positive_tsr} / 30")
col3.metric("Median dividend capacity", f"${median_cap:,.0f}M")
col4.metric("Median adjusted capacity", f"${median_adj:,.0f}M")

st.divider()

# =============================================================================
# 3. TSR COMPARISON
# =============================================================================
st.header("TSR Comparison")
st.caption("Total Shareholder Return = (Closing Price - Opening Price + Dividends Per Share) / Opening Price")

tsr_sorted = filtered.sort_values("tsr", ascending=True)

colors = ["#d62728" if v < 0 else "#1f77b4" for v in tsr_sorted["tsr"]]

fig_tsr = go.Figure(go.Bar(
    x=tsr_sorted["tsr"],
    y=tsr_sorted["ticker"],
    orientation="h",
    marker_color=colors,
    text=[f"{v:.2f}%" for v in tsr_sorted["tsr"]],
    textposition="outside",
    hovertemplate=(
        "<b>%{customdata[0]}</b><br>"
        "TSR: %{x:.2f}%<extra></extra>"
    ),
    customdata=tsr_sorted[["name"]].values,
))

fig_tsr.update_layout(
    title="Total Shareholder Return by Company (fiscal year, sorted ascending)",
    xaxis_title="TSR (%)",
    yaxis_title="Company",
    height=700,
    margin=dict(l=60, r=120, t=60, b=40),
    xaxis=dict(zeroline=True, zerolinecolor="black", zerolinewidth=1),
)

st.plotly_chart(fig_tsr, width="stretch")

st.divider()

# =============================================================================
# 4. DIVIDEND CAPACITY COMPARISON
# =============================================================================
st.header("Dividend Capacity Comparison")
st.caption(
    "Standard capacity follows ACCA AFM methodology (includes share repurchases as a deduction). "
    "Adjusted capacity adds repurchases back to show capacity available for traditional dividends."
)

dc_sorted = filtered.sort_values("adjusted_dividend_capacity", ascending=False)

fig_dc = go.Figure()

fig_dc.add_trace(go.Bar(
    name="Dividend Capacity",
    x=dc_sorted["ticker"],
    y=dc_sorted["dividend_capacity"],
    marker_color="#aec7e8",
    hovertemplate="<b>%{x}</b><br>Dividend Capacity: $%{y:,.0f}M<extra></extra>",
))

fig_dc.add_trace(go.Bar(
    name="Adjusted Dividend Capacity (ex-buybacks)",
    x=dc_sorted["ticker"],
    y=dc_sorted["adjusted_dividend_capacity"],
    marker_color="#1f77b4",
    hovertemplate="<b>%{x}</b><br>Adjusted Capacity: $%{y:,.0f}M<extra></extra>",
))

fig_dc.add_trace(go.Scatter(
    name="Actual Dividends Paid",
    x=dc_sorted["ticker"],
    y=dc_sorted["actual_dividends_paid"],
    mode="markers",
    marker=dict(color="#d62728", size=8, symbol="diamond"),
    hovertemplate="<b>%{x}</b><br>Actual Dividends Paid: $%{y:,.0f}M<extra></extra>",
))

fig_dc.update_layout(
    title="Dividend Capacity vs Adjusted Capacity (sorted by adjusted capacity, descending)",
    xaxis_title="Company",
    yaxis_title="USD Millions",
    barmode="group",
    height=550,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=60, r=40, t=80, b=40),
)

st.plotly_chart(fig_dc, width="stretch")

st.divider()

# =============================================================================
# 5. COMPANY DEEP DIVE
# =============================================================================
st.header("Company Deep Dive")

row = df[df["label"] == selected_label].iloc[0]

st.subheader(f"{row['name']} ({row['ticker']})")
st.caption(f"Sector: {row['sector']} | Fiscal year end: {row['data_as_of'].strftime('%d %b %Y')}")

col_tsr, col_dc = st.columns(2)

# --- TSR Breakdown ---
with col_tsr:
    st.markdown("**Total Shareholder Return**")

    tsr_data = {
        "Item": ["Opening Price", "Closing Price", "Dividends Per Share", "TSR"],
        "Value": [
            f"${row['opening_price']:,.2f}",
            f"${row['closing_price']:,.2f}",
            f"${row['dividends_per_share']:,.2f}",
            f"{row['tsr']:,.2f}%",
        ],
    }
    tsr_df = pd.DataFrame(tsr_data)
    st.dataframe(tsr_df, hide_index=True, width="stretch")

    tsr_val = row["tsr"]
    if tsr_val > 15:
        interpretation = f"{row['ticker']} delivered strong shareholder returns of {tsr_val:.2f}% over the fiscal year, outpacing the broader market average."
    elif tsr_val > 0:
        interpretation = f"{row['ticker']} returned {tsr_val:.2f}% to shareholders over the fiscal year, a modest positive return."
    elif tsr_val > -10:
        interpretation = f"{row['ticker']} posted a small negative return of {tsr_val:.2f}% over the fiscal year."
    else:
        interpretation = f"{row['ticker']} saw a significant decline of {tsr_val:.2f}% over the fiscal year."

    st.markdown(f"*{interpretation}*")

# --- Dividend Capacity Breakdown ---
with col_dc:
    st.markdown("**Dividend Capacity (ACCA AFM Method)**")

    def fmt_m(v):
        if v is None:
            return "N/A"
        return f"${v:,.0f}M"

    dc_data = {
        "Item": [
            "Operating Cash Flow",
            "Less: Tax Paid",
            "Less: Finance Charges",
            "Less: Preference Dividends",
            "Less: Debt Repayment",
            "Less: Share Repurchases",
            "Less: Capital Expenditure",
            "Add: Depreciation & Amortisation",
            "Add: New Debt Proceeds",
            "Add: New Share Proceeds",
            "= Dividend Capacity",
            "= Adjusted Capacity (ex-buybacks)",
            "Actual Dividends Paid",
        ],
        "Value": [
            fmt_m(row["operating_cash_flow"]),
            fmt_m(row["tax_paid"]),
            fmt_m(row["finance_charges"]) if row["finance_charges"] is not None else "N/A (embedded)",
            fmt_m(row["preference_dividends"]),
            fmt_m(row["debt_repayment"]),
            fmt_m(row["share_repurchases"]),
            fmt_m(row["capex"]),
            fmt_m(row["depreciation_amortisation"]),
            fmt_m(row["new_debt_proceeds"]),
            fmt_m(row["new_share_proceeds"]),
            fmt_m(row["dividend_capacity"]),
            fmt_m(row["adjusted_dividend_capacity"]),
            fmt_m(row["actual_dividends_paid"]),
        ],
    }

    dc_df = pd.DataFrame(dc_data)

    def highlight_negatives(val):
        try:
            num_str = val.replace("$", "").replace(",", "").replace("M", "").replace("%", "")
            num = float(num_str)
            if num < 0:
                return "color: red"
        except (ValueError, AttributeError):
            pass
        return ""

    styled = dc_df.style.map(highlight_negatives, subset=["Value"])
    st.dataframe(styled, hide_index=True, width="stretch")

    if row["notes"] and pd.notna(row["notes"]):
        st.warning(f"Note: {row['notes']}")

    cap = row["dividend_capacity"]
    adj = row["adjusted_dividend_capacity"]
    actual = row["actual_dividends_paid"]

    if cap is not None and actual is not None:
        if cap >= actual:
            dc_interp = f"Standard dividend capacity of ${cap:,.0f}M covers actual dividends paid of ${actual:,.0f}M."
        elif adj is not None and adj >= actual:
            dc_interp = (
                f"Standard dividend capacity of ${cap:,.0f}M falls short of actual dividends paid (${actual:,.0f}M), "
                f"but adjusted capacity of ${adj:,.0f}M (excluding buybacks) is sufficient."
            )
        else:
            dc_interp = (
                f"Both standard (${cap:,.0f}M) and adjusted (${adj:,.0f}M) dividend capacity fall short of "
                f"actual dividends paid (${actual:,.0f}M), suggesting reliance on other funding sources."
            )
        st.markdown(f"*{dc_interp}*")

st.divider()

# --- Summary table (all companies) ---
st.subheader("Full Data Table")
st.caption("Click column headers to sort. Negative values are shown in red.")

table_cols = [
    "ticker", "name", "sector", "tsr",
    "dividend_capacity", "adjusted_dividend_capacity", "actual_dividends_paid",
]
table_df = df[table_cols].copy()
table_df.columns = [
    "Ticker", "Company", "Sector", "TSR (%)",
    "Div Capacity ($M)", "Adj Capacity ($M)", "Actual Divs Paid ($M)",
]

def style_negatives(val):
    try:
        if float(val) < 0:
            return "color: red"
    except (TypeError, ValueError):
        pass
    return ""

numeric_cols = ["TSR (%)", "Div Capacity ($M)", "Adj Capacity ($M)", "Actual Divs Paid ($M)"]
styled_table = (
    table_df.style
    .format({
        "TSR (%)": "{:.2f}%",
        "Div Capacity ($M)": "{:,.0f}",
        "Adj Capacity ($M)": "{:,.0f}",
        "Actual Divs Paid ($M)": "{:,.0f}",
    })
    .map(style_negatives, subset=numeric_cols)
)

st.dataframe(styled_table, hide_index=True, width="stretch", height=500)
