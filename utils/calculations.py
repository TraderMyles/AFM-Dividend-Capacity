def calculate_tsr(opening_price, closing_price, dividends_per_share):
    """Returns TSR as a percentage rounded to 2dp, or None if required inputs are missing."""
    if opening_price is None or closing_price is None or opening_price == 0:
        return None
    dps = dividends_per_share or 0
    tsr = (closing_price - opening_price + dps) / opening_price * 100
    return round(tsr, 2)


def calculate_dividend_capacity(
    operating_cash_flow,
    tax_paid,
    finance_charges,
    preference_dividends,
    debt_repayment,
    share_repurchases,
    capex,
    depreciation_amortisation,
    new_debt_proceeds,
    new_share_proceeds,
):
    """
    Returns dividend capacity in millions rounded to nearest million, or None if
    operating_cash_flow is missing.

    Per ACCA AFM methodology:
      OCF - tax - finance charges - pref divs - debt repayment - buybacks
          - capex + D&A + new debt proceeds + new share proceeds
    """
    if operating_cash_flow is None:
        return None

    def v(x):
        return x or 0

    capacity = (
        v(operating_cash_flow)
        - v(tax_paid)
        - v(finance_charges)
        - v(preference_dividends)
        - v(debt_repayment)
        - v(share_repurchases)
        - v(capex)
        + v(depreciation_amortisation)
        + v(new_debt_proceeds)
        + v(new_share_proceeds)
    )
    return round(capacity)


def calculate_adjusted_dividend_capacity(dividend_capacity, share_repurchases):
    """Adds buybacks back to reveal capacity available for traditional dividends."""
    if dividend_capacity is None:
        return None
    return round(dividend_capacity + (share_repurchases or 0))


if __name__ == "__main__":
    # Smoke test against CLAUDE.md AAPL example values
    tsr = calculate_tsr(226.10, 254.74, 1.02)
    assert abs(tsr - 13.11) < 0.01, f"TSR expected 13.11, got {tsr}"

    cap = calculate_dividend_capacity(
        operating_cash_flow=111482,
        tax_paid=43369,
        finance_charges=None,
        preference_dividends=0,
        debt_repayment=10932,
        share_repurchases=90711,
        capex=12715,
        depreciation_amortisation=11698,
        new_debt_proceeds=4481,
        new_share_proceeds=1498,
    )
    assert cap == -28568, f"Dividend capacity expected -28568, got {cap}"

    adj = calculate_adjusted_dividend_capacity(cap, 90711)
    assert adj == 62143, f"Adjusted capacity expected 62143, got {adj}"

    print("All smoke tests passed.")
