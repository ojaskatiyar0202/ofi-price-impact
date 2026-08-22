# Order flow imbalance and short-horizon price impact

We replicate Cont, Kukanov and Stoikov (2014) and then ask the question the paper
does not: whether the relationship it documents is of any use to someone trying
to trade on it.

## The problem

Order flow imbalance measures the net pressure at the top of the book over some
interval. It is built from changes in the size resting at the best bid and ask
rather than from trades, because a cancelled order removes liquidity exactly as a
trade does, and from the book's perspective the two are indistinguishable. Trade
data misses cancellations entirely, and in an electronic market most orders are
cancelled rather than filled.

For each update to the top of book the contribution is

    e_n =  1{P_bid_n >= P_bid_n-1} * q_bid_n  -  1{P_bid_n <= P_bid_n-1} * q_bid_n-1
         - 1{P_ask_n <= P_ask_n-1} * q_ask_n  +  1{P_ask_n >= P_ask_n-1} * q_ask_n-1

The inequalities are weak, and this is what allows one expression to handle three
cases. When the bid price does not change, both bid indicators fire and the
expression reduces to the change in resting size. When the bid improves, only the
first fires and the whole new size counts as inflow, which is correct because the
previous level has not disappeared, it has merely stopped being the best. When
the bid falls, only the second fires and the whole old size counts as outflow.
The ask terms carry the opposite sign because supply at the ask pushes the price
down.

Summing e_n over an interval gives the imbalance for that interval. The paper's
claim is that the midprice change over the interval is close to linear in it,
with a slope that scales like one over the average depth.

## Contemporaneous is not predictive

The paper's regression measures flow and price change over the same interval. It
is therefore a description of what happened rather than a forecast, since by the
time the imbalance is observable the move has already occurred.

The tradeable question is whether imbalance over interval k says anything about
interval k+1. We run both regressions and report them together, because a high
contemporaneous R-squared presented on its own would be misleading.

There is a second hurdle beyond the statistical one. The midprice is a computed
reference and not a price anyone will trade at, so a strategy acting on a
predicted mid move must buy at the ask and sell at the bid, paying the full
spread on a round trip. A prediction of two ticks against a two tick spread
breaks even no matter how accurate it was.

## Method

Top of book is reconstructed into one row per change, with columns for the bid
and ask price and the size resting at each. We sum e_n into fixed clock buckets
and measure the midprice change in ticks from the end of one bucket to the end of
the next. Prices are expressed in ticks throughout so that the price move and the
cost of crossing the spread are directly comparable.

The regression is ordinary least squares with White standard errors, since
bucketed order flow is strongly heteroskedastic and a bucket containing six
hundred events behaves very differently from one containing twenty. The split is
time ordered with no shuffling, and the out-of-sample R-squared applies the
coefficients fitted on the training block to the test block and measures against
the test block's own mean. A model with no predictive content therefore scores at
or below zero rather than merely close to it.

To test the depth claim we refit within depth quintiles. If impact scales like
one over depth then the slope should fall as depth rises while the product of
slope and depth stays roughly flat.

Bucket length is a free parameter and the reported R-squared moves with it, so we
run 1s, 10s and 30s and report all three rather than the most flattering one.

## Data

Results below are from Binance BTCUSDT perpetual futures bookTicker for
30 March 2024, obtained from

    data.binance.vision/?prefix=data/futures/um/daily/bookTicker/BTCUSDT/

The file is 84 MB compressed and is not committed. Download it, unzip into
`data/`, and `analysis.py` runs unchanged. The tick size for this contract is
0.10 rather than the 0.01 typical of an equity, and `make_buckets` is called
accordingly.

Binance publishes bookTicker only for futures and not for spot, and the daily
archives stop partway through 2024. The paper studies US equities, where order
book data of this kind is not freely available.

## Results

| Bucket | Buckets | Contemporaneous R2 in | Contemporaneous R2 out | Predictive R2 out | Predictive t |
|---|---|---|---|---|---|
| 1s | | | | | |
| 10s | | | | | |
| 30s | | | | | |

**Discussion.** [To fill.]

### Depth quintiles

| Quintile | Mean depth | Slope | Slope x depth | Buckets |
|---|---|---|---|---|
| 0 | | | | |
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |

**Discussion.** [To fill.]

## Files

    code/model.py       imbalance, bucketing, regression, depth quintiles
    code/analysis.py    data loading and the runs that produce the tables
    tests/test_ofi.py   tests

## Running it

```bash
pip install -r requirements.txt
python code/analysis.py
pytest tests/ -q
```

Run from the repository root, since the data and results paths are relative to it.

## Limitations

The model has no cost check yet. The predictive regression is reported, but the
comparison of gross edge against the round trip spread is not implemented, so the
second argument above is currently made in prose rather than in numbers.

Only level one is used, so imbalance deeper in the book is invisible. A large
order sitting behind the touch changes how the price responds and does not appear
in this data at all. The data also reports total size at each level rather than
the number of orders composing it, so a level held by one participant and one
held by fifty look identical.

Buckets are fixed in clock time rather than in event count, so a quiet minute and
a busy one carry equal weight in the regression despite containing very different
amounts of information.

The instrument is a crypto perpetual future rather than a US equity. There is no
opening or closing auction, trading runs continuously, and the funding mechanism
that keeps the contract near spot has no equity analogue. The magnitudes here are
therefore not directly comparable to the published figures even where the
qualitative result holds.

## Reference

Cont, R., Kukanov, A. and Stoikov, S. (2014). The price impact of order book
events. *Journal of Financial Econometrics*, 12(1), 47-88.
