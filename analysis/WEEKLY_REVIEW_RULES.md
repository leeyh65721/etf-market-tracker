# Weekly decision quality checks

The weekly ChatGPT report evaluates historical evidence and then decides whether a portfolio adjustment is warranted. **This is not a standing instruction to trade each week.** Only public market research may be written to this GitHub repository. Never store personal holdings, allocation percentages, balances, cash, account values, private P&L, brokerage identifiers, or orders.

## 1. Review historical calls (no hindsight)

For each concrete candidate found in the dated ChatGPT `analysis/daily/` archive, or a specifically dated `analysis/events/` entry:

| Field | Rule |
|---|---|
| Candidate and first-seen date | Distinguish Korea report date from underlying US market date |
| Original claim | Quote/describe the actual view **as of that date**, not revised hindsight |
| Baseline | Verify contemporaneous adjusted close, date, benchmark close, source/version |
| Thesis and counter-thesis | Explain what was asserted and what would invalidate it |
| Objective horizons | Look forward 5, 10 and 20 **US sessions**, when matured |
| Follow-up | Check subsequent comparable adjusted-price returns and SPY excess returns, plus evidence/thesis changes |
| Final status | Confirmed, contradicted, mixed, immature, or insufficient/unavailable data |

**Do not call a 1-day rise a successful 20-day forecast.** Technical-candidate labels are observations, not promises or buy signals. For outcomes, compute return based on the same adjusted-close methodology for both date endpoints. As-of candidates without an authentic dated analyst judgment must not be converted into prior recommendations.


## Forward-only scorecard: technical screen versus actual investment call

A separate **prospective-only technical screen audit** runs in GitHub Actions. It is *not* an estimate of the assistant's recommendation accuracy. Use `data/quality/latest.json`, `data/quality/snapshots/YYYY-MM-DD.json`, and `analysis/quality/latest.md` only after fetching the real files. Never infer they exist simply because a workflow ran.

1. A daily first-captured `data/quality/snapshots/YYYY-MM-DD.json` is **locked on creation**. Same-US-session reruns cannot overwrite baseline ticker prices or historical candidate transitions. Earlier dated ordinary `data/history/` snapshots are not backfilled or disguised as contemporaneously frozen evidence.
2. A new technical candidate is eligible for forward assessment **only** when the immediately prior NYSE session has a locked record and the ticker transitioned from a known noncandidate state into `candidate`. Existing first-day candidates seed the baseline; they are not new investment calls.
3. The technical screen is known after the US close. For avoiding a retrospective same-day purchase, the research comparison starts at the **following NYSE session's frozen adjusted-close proxy**; evaluation ends at the close **5, 10, or 20 NYSE sessions after** that reference. No trade at any of these proxy prices is assumed. NYSE holidays and weekends are skipped by a real exchange calendar.
4. Each candidate gets `pending`, `observed`, or `unverifiable` status per horizon. An absent snapshot on the **exact** entry or exit day must never be filled in with a neighboring date or market return.
5. ETF return and SPY return must use the same observation horizon. The saved `close_usd` values are yfinance's auto-adjusted price snapshots from separate collection times; corporate actions, adjusted-price revisions, delayed prices and rounding can produce distortions. Do not call this verified total returns or executable backtests.
6. Interpret the summary only after enough forward observations mature. `observed=0` means **no supportable hit rate**. Even 30+ observed entries remain exploratory due overlapping tickers, market regime, selection bias and short sample length; it does not prove predictive power.
7. Keep three distinct ledgers: **(a)** mechanical scanner screen transitions and forward SPY price comparisons; **(b)** public analyst thesis, named ETF candidate, date, source, counterargument, falsifier and proposed entry/exit conditions; **(c)** the user's private portfolio decisions and real trades. Do not mix them or publish personal data.

Evaluate whether new prospective evidence justifies improving filters or ranking **only after several distinct market regimes and adequate observations**, and only when comparison with a simple baseline is credible. Do not tune scanner scores opportunistically to recent outcomes. No forecast accuracy, return guarantee, or account drawdown promise is currently established.


## 2. Risk quality gate

Before recommending a changed ETF allocation, consider:

- Single ETF and underlying security concentration and overlaps, including sector/factor/rate/liquidity exposures.
- Correlation of historical **daily returns**, not correlations of closing-price levels; only calculate when there are enough properly aligned observations. State sample dates, number of sessions and source. A short window is unstable.
- Annualized volatility and historical maximum peak-to-trough loss **only if sufficient daily observations exist**. Neither is a forecast or a loss ceiling.
- Currency sensitivity for a Korean investor (USD-priced funds and KRW wealth), and transaction costs/taxes.
- Scenario tests: yields jump, oil spikes, recession/credit stress, semiconductor slump, USD/KRW abrupt change; clearly label assumed shocks and the fact they are scenarios, not predictions.
- The user's maximum tolerable whole-account drawdown is **-15%**, but without cash-flow-adjusted account peaks and up-to-date holdings do **not** claim the current portfolio drawdown or that a recommended mix mathematically respects a guaranteed loss limit.

Private portfolio data must stay in the user's ChatGPT conversation only, not in publicly accessible research files.

## 3. Alternatives on the same footing

At minimum compare **hold existing allocation / shift to a validated new ETF / reduce exposure or increase cash**. If there is no sound new candidate, the new ETF option may be marked ineligible rather than inventing one.

Check thesis, opposing evidence, macro regime, recent relative and absolute returns, fundamentals/valuation, correlation/overlap, loss scenarios, entry timing and fees. Distinguish price momentum from fundamental attractiveness. Check investability (issuer, fund structure, liquid market, AUM, spreads, risk of closure) before treating a technical screen as a trade idea.

Change weights **only if the case is materially stronger than maintaining the allocation**. Otherwise say that no allocation change is justified. If a change is warranted, propose total ETF + cash percentages summing to 100%, within the private ChatGPT report only. The user decides and trades, normally staged across approximately 5-10 US sessions or longer.

## 4. Data integrity and record-availability checklist

- Confirm a file exists and that it was fetched before treating its contents as available.
- Compare `data/latest.json` counts and US date with `data/latest.csv`; compare historical dated snapshots under `data/history/`.
- Technical files `analysis/technical/` do not contain independently verified earnings/news or the ChatGPT macro thesis. Mechanical macro files `analysis/macro/` and `data/macro/` are not a substitute for actual macro-news interpretation.
- Read any successfully saved narrative reports from `analysis/daily/`, `analysis/events/`, and prior `analysis/weekly/`. **Unwritten ChatGPT task output is not archived in GitHub.**
- State missing days, unavailable prices, stale indicators, uncertain ETF flows and incompatible timestamps. Do not interpolate fabricated results.
- Follow up on previous decisions even when today's findings disagree. Prefer changes in evidence over repetition.
- After a GitHub write, re-read the exact file and only then report success. If unattended writing fails, display `GitHub 자동 저장 실패 — 수동 저장 필요`.

## Suggested concise weekly report structure

1. New verified macro, cross-asset and sector evidence (with contradictory evidence)
2. Past candidate scoreboard: matured / mixed / invalidated / still observing
3. Risk concentration and historical correlation where **actually calculable**
4. Existing allocation versus credible alternatives under the same assumptions
5. Final decision: **maintain**, or target weights with trigger conditions; verify source and archive coverage

No brokerage operations. No guarantee of return or limiting market drawdown.
