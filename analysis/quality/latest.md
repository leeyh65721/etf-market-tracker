# ETF technical screen prospective accuracy audit

> **Not investment recommendations or a trading backtest.**
- Latest locked US session: **2026-11-13**
- Verified universe coverage: **95.5%**
- Preserved NYSE sessions: **19**
- Recorded new candidate transitions: **76**
- New locked baseline created on this execution: **True**
- Audit status (data quality only): **OK**

## Observation-to-observation results

| Holding window | Signals | Observed | Awaiting maturity | Unverifiable | Beat SPY | Mean excess | Interpretation |
|---|---:|---:|---:|---:|---:|---:|---|
|5 NYSE sessions|76|59|17|0|37/59|-0.428pp|exploratory_only|
|10 NYSE sessions|76|42|34|0|30/42|+0.956pp|exploratory_only|
|20 NYSE sessions|76|0|76|0|0/0|n/a|insufficient_observations|

## Freshness and quality concerns

- None identified in the mechanical check.

## Evaluation rules

- NYSE trading calendar is used, not calendar or weekday approximations.
- Capture is frozen at first successful GitHub publishing day; same-day reruns do not overwrite the locked baseline.
- Only NEW technical-candidate transitions after a known consecutive prior NYSE session are evaluated. First archived session only seeds the baseline.
- Signal becomes known AFTER its market-session close; entry reference = the NEXT NYSE session CLOSE; exit reference = exact 5/10/20 NYSE sessions after this.
- If the reference day is missing, result is explicitly unverifiable, never interpolated.
- Relative return uses frozen Yahoo auto-adjusted close snapshots; corporate actions and later provider revisions can distort comparability.
- Technical labels are not ChatGPT investment recommendations; no actual portfolio, orders, FX, costs or P&L.
- Until enough future observations mature, there is **no supported predictive accuracy estimate**.
