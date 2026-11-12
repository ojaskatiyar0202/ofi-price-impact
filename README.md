# Order flow imbalance and short-horizon price impact

We replicate Cont, Kukanov and Stoikov (2014) and examine whether order flow
imbalance predicts short-horizon price movement. We then compare the predicted
move against the cost of crossing the spread.

## Order flow imbalance

Order flow imbalance measures the net pressure at the top of the book over an
interval. It is built from changes in the size available at the best bid and ask
rather than from trades. A cancelled order removes size just as a trade does, and
the book looks the same either way, so a measure built on trades alone misses much
of what happens.

To give further intuition, size at the bid is demand and size at the ask is supply.
Demand appearing pushes the price up and demand withdrawing pushes it down. Supply
appearing pushes the price down and supply withdrawing pushes it up. Those four
events are what the expression below counts, and their signs follow from that.

For each update to the top of book, the contribution is

```math
\large e_n = \mathbf{1}\{P^b_n \ge P^b_{n-1}\}\, q^b_n - \mathbf{1}\{P^b_n \le P^b_{n-1}\}\, q^b_{n-1} - \mathbf{1}\{P^a_n \le P^a_{n-1}\}\, q^a_n + \mathbf{1}\{P^a_n \ge P^a_{n-1}\}\, q^a_{n-1}
```

where $P^b_n$ and $q^b_n$ are the best bid price and the size available at it after
the $n$-th update, and $P^a_n$ and $q^a_n$ are the same for the ask.

The inequalities are weak, which is what allows one expression to cover three
cases. Take the bid side; the ask works the same way, and the two are added
together at the end.

The price comparison decides which case applies, and the size is what gets counted
in that case. If the price is unchanged, both indicators equal one and the two
terms become $q^b_n - q^b_{n-1}$, the change in size at that same price. If the price
has risen, only the first indicator holds and the term is $q^b_n$, the whole size at
the new level. The old size is not subtracted because it sits at a different price
and that level still exists, one tick below. If the price has fallen, only the
second holds and the term is $-q^b_{n-1}$, the whole size at the level that is no
longer best.

The ask terms carry the inequalities reversed, and the signs flipped, since size
arriving at the ask is supply and pushes the price down.

Summing $e_n$ over an interval gives the imbalance for that interval. The paper finds
that the midprice change is roughly a constant times that imbalance, and that the
constant scales by one over the average depth. Depth here means the average of the
size at the best bid and the best ask. The idea is that the same imbalance matters
more when there is less size sitting there. If 400 units are removed from an ask
holding 500, the level is nearly cleared and the price has to move. If the ask were
holding 10,000 the same 400 would be a 4% reduction. So the slope should be larger
when there is less depth, and if the relationship is exactly one over depth, slope
multiplied by depth would be constant.

## Contemporaneous and predictive regressions

The paper's regression measures flow and price change over the same interval, so
it describes a move that has already happened rather than forecasting one. We
therefore also regress the price change over interval $k+1$ on the imbalance over
interval $k$, and report both.

A predictive relationship would still have to clear the cost of trading on it. The
midprice is a computed reference rather than a price anyone will transact at, so
acting on a predicted mid move means buying at the ask and selling at the bid,
paying the full spread over a round trip. A prediction of two ticks against a two
tick spread breaks even regardless of its accuracy.

## Method

Top of book is reconstructed into one row per change, with columns for the bid and
ask price and the size available at each. We sum $e_n$ into fixed clock buckets and
measure the midprice change in ticks from the end of one bucket to the end of the
next. Prices are in ticks so that the price move and the cost of crossing the
spread are directly comparable.

The regression is ordinary least squares of the midprice change on the imbalance.
The null hypothesis is that the coefficient on imbalance is zero, meaning order flow
tells us nothing about the price. We reject it at the 5% level when the test statistic
exceeds the critical value 1.96.

Standard errors use White's correction, because the size of the errors varies a lot
across buckets: a bucket with six hundred events is far noisier than one with
twenty, and the usual formula would understate the uncertainty.

The training and test blocks are split by time with no shuffling, 70% and 30%. A
random split would train on the afternoon to predict the morning. The out-of-sample
figure takes the coefficients from the training block, applies them to the test
block, and compares the result against simply predicting the test block's average.
A model that adds nothing scores zero or below.

To test the depth claim, we refit within depth quintiles. If impact scales like one
over depth then the slope should fall as depth rises while the product of slope and
depth stays roughly flat.

For the cost comparison, we take the fitted predictive coefficient, trade its sign on
the test block, and measure the realised next-bucket move. That move is demeaned
over the test block, so a strategy that happens to sit long through a rising market
is not credited with the drift. Cost is the average spread over the buckets traded.
The mid is a computed reference rather than an actual trading price, so a round trip
means buying at the ask and selling at the bid, which pays the full spread once.

Bucket length is a free parameter and the reported R-squared moves with it, so we
run 1s, 10s and 30s and report all three.

## Data

Results below are from Binance BTCUSDT perpetual futures bookTicker for
30 March 2024, obtained from

    data.binance.vision/?prefix=data/futures/um/daily/bookTicker/BTCUSDT/

We used futures rather than spot because Binance only publishes bookTicker for
futures. It should be noted that Cont, Kukanov and Stoikov use US equities, but
equity order book data was not available to us.

The file is 84 MB and is not committed, since it can be downloaded from the link
above. We unzipped it into `data/` and ran `analysis.py` from the repository root.
The tick size on this contract is 0.10, not the 0.01 you would see on an equity, so
`make_buckets` is called with that.

## Results

| Bucket | Buckets | Contemporaneous $R^2$ in | Contemporaneous $R^2$ out | Predictive $R^2$ out | Predictive $t$ |
|---|---:|---:|---:|---:|---:|
| 1s | 86,396 | 0.5739 | 0.5957 | 0.0372 | 30.67 |
| 10s | 8,639 | 0.7116 | 0.7244 | 0.0054 | 3.81 |
| 30s | 2,879 | 0.7042 | 0.7317 | -0.0040 | 0.90 |

**Discussion.** The contemporaneous relationship is strong and stable. R-squared
rises from 0.57 at one second to 0.72 at ten, and the out-of-sample figure is
slightly higher than the in-sample figure at every bucket length, so it seems
the relationship holds on the last 30% of the day as well. The rise with bucket length is a
measurement effect rather than a change in the relationship itself. Longer buckets
contain more events, the noise in each partly cancels, and what is left is the
systematic part. The gain flattens between ten and thirty seconds.

The predictive regression behaves differently. Out-of-sample R-squared falls from
0.037 at one second to 0.005 at ten and to -0.004 at thirty, where the fitted line
does slightly worse than predicting the test block's mean. The t-statistic follows
the same path, from 30.7 to 3.8 to 0.9.

The one-second result is worth taking a closer look at. A t-statistic of 30.7 across 86,396 buckets means
the coefficient is not zero, and that much is clear. But the same regression
explains 3.7% of the variation in the next second's price change. The relationship is statistically significant but seems economically small. Whether a
signal this weak is worth trading depends on what it costs to capitalise on it,
which the cost comparison below tests.

### Cost comparison

| Bucket | Hit rate | Gross (ticks) | Cost (ticks) | Net (ticks) |
|---|---:|---:|---:|---:|
| 1s | 0.530 | 3.87 | 1.04 | 2.83 |
| 10s | 0.560 | 11.21 | 1.09 | 10.12 |
| 30s | 0.537 | 10.07 | 1.10 | 8.97 |

**Discussion.** After paying the spread, the strategy makes money at all three
bucket lengths. The gross figures line up with the R-squared. An eleven tick edge at
ten seconds implies the next bucket moves with a standard deviation of around 190
ticks, or about 48% annualised, which is normal for Bitcoin.

The thirty-second row looks contradictory. Out-of-sample R-squared is negative, so
the fitted line predicts worse than just guessing the average, yet the strategy
still makes money. The reason is that R-squared measures how close the predicted
size of the move is, while the strategy only uses the direction. The coefficient is
too large, so it predicts big moves where small ones happen, but it still gets the
sign right more often than not.

The cost model is optimistic, and whether it translates to an actual strategy is
another question entirely. It assumes the trade executes at the observed spread with
no market impact, no delay between observing the bucket close and transacting, no
queue position and no partial fills. It also ignores that the market makers being
traded against see the same order flow.

### Depth quintiles

| Quintile | Mean depth | Slope | Slope $\times$ depth | Buckets |
|---|---:|---:|---:|---:|
| 0 | 3.156 | 1.114 | 3.517 | 1,728 |
| 1 | 4.080 | 0.948 | 3.867 | 1,728 |
| 2 | 4.735 | 0.779 | 3.686 | 1,727 |
| 3 | 5.465 | 0.722 | 3.946 | 1,728 |
| 4 | 8.126 | 0.624 | 5.071 | 1,728 |

**Discussion.** The slope falls as depth rises, from 1.114 in the thinnest quintile
to 0.624 in the thickest, without reversing anywhere. That is the direction the
mechanism predicts, since a given imbalance clears more of a thin book than a thick
one and so moves the price further.

The size of the effect does not match the paper's claim. Under exact one over depth
scaling the product of slope and depth would be constant. It holds across the first
four quintiles, from 3.52 to 3.95 around a mean of 3.75, then rises to 5.07 in the
top quintile, 35% above that mean. Fitting a power law across all five points gives
a slope proportional to $\text{depth}^{-0.63}$ rather than $\text{depth}^{-1}$, with an
$R^2$ of 0.94 on the log-log fit.

So depth does scale impact, but more weakly than one over depth.
Mean depth only ranges from 3.2 to 8.1 across the quintiles, which
is a narrow range over which to identify an exponent, and the deviation sits in the
quintile furthest from the rest. A wider set of instruments would test this better
than one contract on one day.

## Files

    code/model.py       imbalance, bucketing, regression, depth quintiles, cost check
    code/analysis.py    data loading and the runs that produce the tables

## Running it

```bash
pip install -r requirements.txt
python code/analysis.py
```

Run from the repository root, since the data and results paths are relative to it.

## Limitations

The cost model assumes execution at the observed spread. It ignores market impact,
delay, queue position and partial fills, all of which work against the strategy.
It also assumes we always take the price on offer, the ask when buying and the bid
when selling. Posting an order and waiting would get a better price, though it
risks not being filled at all.

Imbalance deeper in the book is invisible; that is to say, a large order sitting one
or two levels down changes how the price responds and does not appear in this data.
The data also reports total size at each level rather than the number of orders
making it up, so a level held by one participant and one held by fifty are identical
here.

Buckets are fixed in clock time rather than in event count, so a period with very
few changes and one with many carry equal weight in the regression despite
containing very different amounts of information.

Results come from one instrument on one day, so these figures cannot be
taken as characteristic of the market generally.

The instrument is a crypto perpetual future rather than a US equity. There is no
opening or closing auction; trading runs continuously, and the funding mechanism
that keeps the contract near spot has no equity analogue. The magnitudes are not
directly comparable to the published figures.

## Reference

Cont, R., Kukanov, A. and Stoikov, S. (2014). The price impact of order book
events. *Journal of Financial Econometrics*, 12(1), 47-88.
