# Dow 30 Shareholder Analysis

A static financial analysis tool that calculates and visualises **Total Shareholder Return (TSR)** and **Dividend Capacity** for all 30 Dow Jones Industrial Average companies.

Built using ACCA Advanced Financial Management (AFM/P4) methodology. Data is sourced once from the Financial Modeling Prep API and stored as static JSON — this is not a live dashboard.

## What it shows

- **TSR** — fiscal year share price return including dividends, ranked across all 30 companies
- **Dividend Capacity** — free cash flow available for dividends per the ACCA AFM formula
- **Adjusted Dividend Capacity** — same figure with share buybacks added back, for comparison
- **Company Deep Dive** — full input/output breakdown for any individual company

## Stack

- [Streamlit](https://streamlit.io) — app framework
- [Plotly](https://plotly.com/python/) — charts
- Static JSON data in `/data/`

## Run locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Refresh the data

Requires a [Financial Modeling Prep](https://financialmodelingprep.com) API key.

```bash
echo "FMP_API_KEY=your_key_here" > .env
python scripts/fetch_data.py
```

This overwrites `data/tsr.json` and `data/dividend_capacity.json` with live figures.

## Formulas

**TSR**
```
(Closing Price - Opening Price + Dividends Per Share) / Opening Price
```

**Dividend Capacity (ACCA AFM)**
```
Operating Cash Flow
- Tax Paid
- Finance Charges
- Preference Dividends
- Debt Repayment
- Share Repurchases
- Capital Expenditure
+ Depreciation & Amortisation
+ New Debt Proceeds
+ New Share Proceeds
```

## Notes

- Fiscal year end dates vary across the 30 companies
- Finance charges are not separately disclosed by all companies — noted where applicable
- Share repurchases are included in the standard formula per ACCA methodology; the adjusted figure removes them
