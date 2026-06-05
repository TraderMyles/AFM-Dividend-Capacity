"""
One-time FMP data pull script. Run locally; never imported by the Streamlit app.

Usage:
    export FMP_API_KEY=your_key_here
    python scripts/fetch_data.py

Or place FMP_API_KEY=... in a .env file at the project root.

Writes:
    data/tsr.json
    data/dividend_capacity.json

Reads:
    data/companies.json  (for tickers and fiscal year end dates)
"""

import json
import os
import sys
import time
from datetime import date, timedelta, datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

# Allow running from repo root or from scripts/
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.calculations import (
    calculate_tsr,
    calculate_dividend_capacity,
    calculate_adjusted_dividend_capacity,
)

load_dotenv(ROOT / ".env")

API_KEY = os.environ.get("FMP_API_KEY")
if not API_KEY:
    sys.exit("Error: FMP_API_KEY not set. Add it to your .env file or export it.")

BASE = "https://financialmodelingprep.com/api/v3"


def get(path: str, **params) -> dict | list:
    params["apikey"] = API_KEY
    url = f"{BASE}{path}"
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()


def get_cash_flow(ticker: str, fiscal_year_end: str) -> dict | None:
    """Return the cash flow statement record matching the given fiscal year end date."""
    try:
        data = get(f"/cash-flow-statement/{ticker}", period="annual", limit=3)
    except Exception as e:
        print(f"  [ERROR] Cash flow fetch failed for {ticker}: {e}")
        return None

    if not data or isinstance(data, dict):
        print(f"  [WARN] No cash flow data for {ticker}")
        return None

    # Try exact match first, then nearest within 5 days
    target = date.fromisoformat(fiscal_year_end)
    for record in data:
        record_date = date.fromisoformat(record.get("date", "1900-01-01"))
        if abs((record_date - target).days) <= 5:
            return record

    # Fall back to most recent record and warn
    print(f"  [WARN] {ticker}: no cash flow record within 5 days of {fiscal_year_end}. Using most recent.")
    return data[0] if data else None


def get_price_on(ticker: str, target: date, direction: str = "nearest") -> float | None:
    """
    Return the closing price nearest to target date.

    direction="first" → earliest price in the window (fiscal year open)
    direction="last"  → latest price in the window (fiscal year close)
    """
    from_d = target - timedelta(days=7)
    to_d = target + timedelta(days=7)
    try:
        data = get(
            f"/historical-price-full/{ticker}",
            **{"from": from_d.isoformat(), "to": to_d.isoformat()},
        )
    except Exception as e:
        print(f"  [ERROR] Price fetch failed for {ticker} around {target}: {e}")
        return None

    prices = data.get("historical", []) if isinstance(data, dict) else []
    if not prices:
        print(f"  [WARN] No price data for {ticker} around {target}")
        return None

    # historical is sorted descending (newest first)
    if direction == "first":
        return prices[-1]["close"]  # oldest in the window
    return prices[0]["close"]  # newest in the window


def get_dividends_in_period(ticker: str, fy_start: date, fy_end: date) -> float:
    """Sum of dividends per share paid/declared between fy_start and fy_end."""
    try:
        data = get(f"/historical-price-full/stock_dividend/{ticker}")
    except Exception as e:
        print(f"  [ERROR] Dividend fetch failed for {ticker}: {e}")
        return 0.0

    historical = data.get("historical", []) if isinstance(data, dict) else []
    total = 0.0
    for entry in historical:
        try:
            d = date.fromisoformat(entry["date"])
        except (KeyError, ValueError):
            continue
        if fy_start <= d <= fy_end:
            total += entry.get("adjDividend") or entry.get("dividend") or 0.0
    return round(total, 4)


def extract_cf_field(record: dict, *keys: str) -> int | None:
    """Return the first non-None value from the record for the given keys."""
    for key in keys:
        val = record.get(key)
        if val is not None:
            return int(val)
    return None


def process_company(company: dict) -> tuple[dict, dict, list[str]]:
    """
    Fetch all data for one company and return (tsr_record, dc_record, null_fields).
    """
    ticker = company["ticker"]
    fy_end = date.fromisoformat(company["fiscal_year_end"])
    fy_start = fy_end - timedelta(days=365)

    print(f"\n{ticker} — FY end {fy_end}")

    # --- Cash flow ---
    cf = get_cash_flow(ticker, company["fiscal_year_end"])
    time.sleep(0.3)  # stay within free-tier rate limits

    ocf = extract_cf_field(cf, "operatingCashFlow") if cf else None
    tax = extract_cf_field(cf, "taxesPaid", "incomeTaxesPaid") if cf else None
    finance = extract_cf_field(cf, "interestPaid") if cf else None
    pref_divs = 0
    debt_repay = extract_cf_field(cf, "debtRepayment", "repaymentOfDebt") if cf else None
    buybacks = extract_cf_field(cf, "commonStockRepurchased") if cf else None
    capex = extract_cf_field(cf, "capitalExpenditure") if cf else None
    da = extract_cf_field(cf, "depreciationAndAmortization") if cf else None
    new_debt = extract_cf_field(cf, "proceedsFromIssuanceOfDebt", "debtIssuance") if cf else None
    new_shares = extract_cf_field(cf, "commonStockIssued", "proceedsFromIssuanceOfCommonStock") if cf else None
    actual_divs = extract_cf_field(cf, "dividendsPaid", "commonDividendsPaid") if cf else None

    # capex and debt_repayment are typically negative in FMP — take absolute value
    if capex is not None and capex < 0:
        capex = abs(capex)
    if debt_repay is not None and debt_repay < 0:
        debt_repay = abs(debt_repay)
    if buybacks is not None and buybacks < 0:
        buybacks = abs(buybacks)
    if actual_divs is not None and actual_divs < 0:
        actual_divs = abs(actual_divs)
    if new_debt is not None and new_debt < 0:
        new_debt = abs(new_debt)
    if new_shares is not None and new_shares < 0:
        new_shares = abs(new_shares)

    # --- Prices ---
    opening_price = get_price_on(ticker, fy_start, direction="first")
    time.sleep(0.3)
    closing_price = get_price_on(ticker, fy_end, direction="last")
    time.sleep(0.3)

    # --- Dividends ---
    dps = get_dividends_in_period(ticker, fy_start, fy_end)
    time.sleep(0.3)

    # --- Finance charge note ---
    notes = None
    if finance is None:
        notes = "Finance charges (interest paid) not separately disclosed in the cash flow statement."

    # --- Compute ---
    tsr = calculate_tsr(opening_price, closing_price, dps)
    cap = calculate_dividend_capacity(ocf, tax, finance, pref_divs, debt_repay, buybacks, capex, da, new_debt, new_shares)
    adj = calculate_adjusted_dividend_capacity(cap, buybacks)

    tsr_record = {
        "ticker": ticker,
        "opening_price": opening_price,
        "closing_price": closing_price,
        "dividends_per_share": dps,
        "tsr": tsr,
    }

    dc_record = {
        "ticker": ticker,
        "operating_cash_flow": ocf,
        "tax_paid": tax,
        "finance_charges": finance,
        "preference_dividends": pref_divs,
        "debt_repayment": debt_repay,
        "share_repurchases": buybacks,
        "capex": capex,
        "depreciation_amortisation": da,
        "new_debt_proceeds": new_debt,
        "new_share_proceeds": new_shares,
        "dividend_capacity": cap,
        "adjusted_dividend_capacity": adj,
        "actual_dividends_paid": actual_divs,
        "notes": notes,
    }

    null_fields = [k for k, v in {**tsr_record, **dc_record}.items() if v is None and k not in ("finance_charges", "notes")]

    return tsr_record, dc_record, null_fields


def main():
    companies_path = ROOT / "data" / "companies.json"
    companies = json.loads(companies_path.read_text())

    tsr_results = []
    dc_results = []
    summary_rows = []

    for company in companies:
        tsr_rec, dc_rec, nulls = process_company(company)
        tsr_results.append(tsr_rec)
        dc_results.append(dc_rec)
        summary_rows.append((company["ticker"], tsr_rec.get("tsr"), dc_rec.get("dividend_capacity"), nulls))

    (ROOT / "data" / "tsr.json").write_text(json.dumps(tsr_results, indent=2))
    (ROOT / "data" / "dividend_capacity.json").write_text(json.dumps(dc_results, indent=2))

    print("\n" + "=" * 70)
    print(f"{'Ticker':<8} {'TSR %':>8} {'Div Cap $M':>12}  Null fields")
    print("-" * 70)
    for ticker, tsr, cap, nulls in summary_rows:
        tsr_s = f"{tsr:.2f}%" if tsr is not None else "N/A"
        cap_s = f"{cap:,.0f}" if cap is not None else "N/A"
        null_s = ", ".join(nulls) if nulls else "-"
        print(f"{ticker:<8} {tsr_s:>8} {cap_s:>12}  {null_s}")

    print("=" * 70)
    print(f"\nWritten: data/tsr.json ({len(tsr_results)} records)")
    print(f"Written: data/dividend_capacity.json ({len(dc_results)} records)")


if __name__ == "__main__":
    main()
