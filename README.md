# Order flow imbalance and price impact

A replication of Cont, Kukanov and Stoikov (2014), *The Price Impact of Order Book
Events*, extended with the question the paper does not ask: once you account for
the spread, is any of this tradeable.

## The question

Order flow imbalance (OFI) aggregates changes at the top of the book into a single
signed number per interval. The paper's central claim is that midprice changes are
close to linear in OFI, with a slope that scales roughly like one over average
depth. That result is *contemporaneous*: it explains moves using flow measured
over the same interval.

Two things follow that the paper leaves implicit, and both are the point of this
repo.

1. A contemporaneous R² is not a forecast. By the time OFI over interval *k* is
   observable, the move over interval *k* has happened. The tradeable question is
   whether OFI over *k* says anything about interval *k+1*.
2. Even a real forecast has to clear the round-trip cost of crossing the spread
   twice. A signal worth a fraction of a tick against a one-tick spread is not a
   strategy.

So three regressions get run and reported side by side, and the cost check is
applied to the predictive one.

## Method

- Reconstruct top of book from message data into a canonical frame:
  `ts, bid_px, bid_sz, ask_px, ask_sz`, one row per change at the touch.
- Compute the per-event contribution `e_n` exactly as in the paper. Weak
  inequalities matter: unchanged bid price collapses to the change in resting
  size, an improving bid counts the whole new size as inflow, a falling bid
  counts the whole old size as outflow.
- Sum `e_n` into fixed clock buckets. Measure midprice change in ticks from
  end-of-bucket mid to end-of-bucket mid.
- Fit OLS with White HC0 standard errors, split by time with no shuffling.
  Out-of-sample R² applies train coefficients to the held-out block and measures
  against the test mean, so a useless model scores at or below zero.
- Refit inside depth quintiles to test the one-over-depth scaling claim.
- Take the predictive fit at face value, trade its sign on the test block, and
  compare gross edge in ticks against spread plus fees.

## Running it

```bash
pip install -r requirements.txt
pytest tests/ -q                      # 11 tests pinning the OFI definition
python -m src.run --source synthetic  # end-to-end check, no data needed
```

Real data:

```bash
python -m src.run --source binance --path data/BTCUSDT-bookTicker-2026-01-05.csv --tick-size 0.01
python -m src.run --source lobster --path data/AAPL_2026-01-05 --date 2026-01-05
```

`--freq` sets bucket length and matters a lot. Start at `10s`, then check `1s` and
`30s`, because the reported R² is partly an artefact of bucket choice.

## Data

Nothing is committed. Two free sources work out of the box.

- **LOBSTER** publishes a free sample of message and orderbook files for a few
  US names. Level 1 is enough here.
- **Binance** publishes `bookTicker` archives at `data.binance.vision`, one row
  per best bid or ask change, no API key. Confirm the path for your symbol and
  date before scripting a bulk pull, the layout has changed before.

A synthetic book simulator is included so the code can be exercised without any
download. **Numbers from synthetic data describe the simulator, not a market.**
They belong nowhere near the results table below.

## Results

Empty until run on real data. Fill from `results/summary_*.json`.

| Regression | beta | t | R² in | R² out |
|---|---|---|---|---|
| Contemporaneous, raw OFI | | | | |
| Contemporaneous, OFI / depth | | | | |
| Predictive, raw OFI | | | | |
| Predictive, OFI / depth | | | | |

Depth scaling. If the paper's claim holds, `beta` falls across quintiles while
`beta × depth` stays roughly flat.

| Depth quintile | Mean depth | beta | beta × depth |
|---|---|---|---|
| | | | |

Cost check on the predictive fit, test block only.

| Metric | Value |
|---|---|
| Trades | |
| Hit rate | |
| Gross edge (ticks) | |
| Round-trip cost (ticks) | |
| Net edge (ticks) | |

## What did not work

Fill in honestly as you go. Candidates from the design:

- Contemporaneous R² is high and means nothing for trading. Worth stating plainly
  because the gap between the two numbers is the whole finding.
- Predictive R² is expected to be near zero at 10s buckets on liquid names.
- Net of a one-tick round trip, a sub-tick gross edge is dead. Record the number
  rather than burying it.
- Bucket length is a free parameter and the headline R² moves with it. Note the
  sensitivity instead of reporting the flattering choice.

## Reference

Cont, R., Kukanov, A. and Stoikov, S. (2014). The Price Impact of Order Book
Events. *Journal of Financial Econometrics*, 12(1), 47–88.
