# btc-cent-forecast-01

Forecast Bitcoin's US-dollar price 240 minutes (4 hours) after a checkpoint,
from the 4,320 one-minute closes of the 72 hours up to that checkpoint.

## Method

The 4-hour-ahead price is close to a random walk, so the honest middle
estimate (the conditional median) is near the last price. But the pool's
price has microstructure noise -- one large trade can spike a single
minute's close -- and a mild pull back toward its recent level. The
forecast therefore blends three robust levels:

- 55% the last close,
- 22.5% the median of the last 45 closes (a spike-proof "current price"),
- 22.5% an exponentially weighted mean with a 240-minute half-life (the
  slower level the price tends to drift back toward).

No trend is extrapolated: on the kit's practice history, extrapolating the
last 1-4h slope made the error worse, so the forecast never chases momentum.

## Backtest

Kit's 6 practice cases, 330 causal pseudo-checkpoints:

| forecaster | 60-min grid MAE | 4h grid MAE |
|---|---|---|
| persistence (house baseline) | 45,117 cents | 40,950 cents |
| this blend | 43,384 cents | 38,117 cents |

About 4-6% better than persistence on the pseudo-case grids. On the five
real practice checkpoints (p00-p04, one sustained downtrend) the blend
scores 50,110 cents vs persistence's 47,055 -- a gap within one standard
error of a 5-case mean, and the reason the shrink weight is 0.45 rather
than the heavier 0.60 that scored best on the grids: the final's twelve
checkpoints are unseen prices in unknown regimes, so the middle weight
hedges that risk.

Why a 45-close median window instead of 60: the practice cases sit in one
sustained downtrend, where a 60-close median runs stale-high (up to +$428
above the last price). The shorter window improves practice and both grids
without losing any grid win.

## Run

```sh
python3 main.py
```

Reads `$MAKEFUN_INPUT_DIR` (else `/input`) and writes one
`/output/<id>.out` per `/input/<id>.in`:

```json
{"forecasts": [{"case": "p00", "price": 74773.49}]}
```

Python 3.13, standard library only, deterministic, ~0.02 s per case.
