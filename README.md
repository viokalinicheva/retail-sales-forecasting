# Retail Sales Forecasting During Structural Change

A transparent failure analysis: good historical validation does not guarantee reliable planning when a sales series changes regime.

## Question and measure

Can an interpretable historical trend support a twelve-month planning baseline? The measure is **U.S. retail trade sales excluding food services**, in **millions of nominal U.S. dollars**, adjusted for seasonal, holiday, and trading-day differences—not price changes. The scope is January 1992–June 2021.

## Verified source and acquisition

**All 354 observations exactly match a reconstruction from original Census archives**, with maximum absolute difference zero. The 30-year wide input has 360 potential monthly cells; six blanks represent July–December 2021, after its endpoint. No historical sales values are imputed or removed. Invalid numeric values and duplicate months fail validation.

The default workflow requires no course file or FRED/ALFRED download. It acquires:

- [Census 2021 benchmark workbook](https://www.census.gov/retail/mrts/www/benchmark/2021/excel/benchsales21.xls): second `Retail sales, total` row under `ADJUSTED` on each annual sheet, January 1992–March 2021.
- [May 14, 2021 release](https://www2.census.gov/retail/releases/historical/marts/adv2104.pdf), [June 15 release](https://www2.census.gov/retail/releases/historical/marts/adv2105.pdf), and [July 16 release](https://www2.census.gov/retail/releases/historical/marts/adv2106.pdf): Table 1, adjusted Retail row. Later releases supersede earlier values.

All four files are SHA-256 checked. The workbook supplies 351 months; the releases revise six existing values and append April–June 2021. The canonical date/value digest is `d68199ed407e7436e37a7063d0d80ffc067236a3f2813adbb4c0753719752543`. [sources.json](sources.json) records hashes, column dates, extracted values, and revision order. CSV formatting differs from the original course file, but every numerical observation agrees.

Definitions are supported by [Census time-series documentation](https://www.census.gov/retail/marts/www/timeseries.html) and release notes. [FRED RSXFS metadata](https://fred.stlouisfed.org/series/RSXFS) independently corroborate identity only; FRED services content is not an acquisition dependency. Sources checked October 28, 2026.

## Method and vintage limitation

Train on **342 months through June 2020** and reserve **July 2020–June 2021** for final evaluation. Compare linear trend, trend plus month indicators, and seasonal naive at five expanding-window validation origins, July 2015–July 2019, each forecasting twelve months. Fit preprocessing within each fold; select by average validation RMSE before examining test results. Report all three predeclared test baselines diagnostically, not for another selection round.

**This is a fixed-July-16-2021-vintage retrospective backtest, not a real-time historical forecast.** Revised inputs postdate nominal forecast origins. Chronological target separation prevents fitting on test targets but does not remove publication-vintage information advantages. A real-time study needs an archived vintage at each origin.

## Verified results

| Method | Mean validation RMSE | Final-test RMSE |
|---|---:|---:|
| Linear trend—selected | 11,343.17 | 66,432.63 |
| Trend plus month indicators | 11,370.49 | 66,597.43 |
| Seasonal naive | 16,301.33 | 80,273.26 |

Errors are **millions of nominal dollars**. Selected-model test MAE is **60,125.81 million dollars**. RMSE is **12.91% of mean test sales**, a normalization rather than MAPE. The model underpredicts all twelve months; test RMSE is **5.86 times** mean validation RMSE. This is an honest baseline failure, not a production-ready forecasting claim.

Inspect the [executed notebook](retail_sales_forecasting.ipynb) and [validation record](validation.json). Eight code cells execute from a fresh kernel, all three charts are embedded, and no saved errors remain. A rerun also saves local `outputs/` figures, which are not part of the root-only public release.

## Reproduce

Use Python **3.12** (verified 3.12.14):

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m ipykernel install --sys-prefix --name python3
python run.py
```

Without `PROJECT_DATA_DIR`, the first run downloads only the four pinned **Census** archives into ignored `.local/census-sources/`. Every run parses these raw archives, reconstructs all values, checks their canonical digest, clears saved notebook state, and executes every cell. This is not an aggregate-cache replay; subsequent runs can work offline with the verified original archives.

Optionally use `PROJECT_DATA_DIR=/path/to/source/directory python run.py` with the unchanged original `us_retail_sales.csv`. Its byte hash must be `fa034d22a15c7ce4ccfceba8221d9fd87fe9ceeccbf495b2123601f9e8f73b86`, and canonical values must also match. Originals are never modified. No credentials or API keys are needed.

## Limits, rights, and decision

Nominal growth is not inflation-adjusted growth. One test year is not twelve independent experiments. Revised inputs, underlying survey error, a simple trend, and unmodeled economic drivers constrain conclusions. No causal explanation, current forecast, prediction interval, or real-time-vintage accuracy is claimed. Monitor signed errors and evaluate alternatives on a new time-separated holdout.

[Census DS027, page 9](https://www2.census.gov/foia/ds_policies/ds027.pdf) states that employee-created data/works generally are not copyright protected in the United States, with exceptions and possible foreign rights. This package attributes the government tables, does not redistribute archives, and implies no endorsement. Original code and writing are MIT; underlying statistics are not claimed as original intellectual property.

Eight release files plus chart images: README, notebook, `run.py`, requirements, `.gitignore`, validation, sources, and license. Cleanup resolves identity, units, vintage, and public acquisition while preserving original course material elsewhere.

Method reference: Hyndman, R. J., & Athanasopoulos, G. (2021). *Forecasting: Principles and practice* (3rd ed.), [The forecaster's toolbox](https://otexts.com/fpp3/toolbox.html). Retrieved October 28, 2026. This supports evaluation methods, not real-time availability of revised inputs.
