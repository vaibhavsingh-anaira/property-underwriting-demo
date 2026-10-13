# Extensions: where more value is

Each candidate below was checked against real data before being listed. "Measured" figures are Manhattan, taken on
13 Oct 2026 from the linked datasets; nothing is estimated. Underwriting relevance is cited where an outside source exists.

## Ranked

| # | Extension | Underwriting question it answers | Data (verified link) | Measured | Main limit |
|---|---|---|---|---|---|
| 1 | **Employee count and industry check** | Is the declared headcount / class plausible? (workers' comp premium is rated on payroll by class) | [SBA PPP loan-level data](https://data.sba.gov/dataset/ppp-foia): borrower name, address, NAICS, jobs reported, payroll proceeds, business age | 10,144 Manhattan restaurant loans; **18%** of our businesses matched (14 of 15 sampled matches clearly correct, 1 unclear); median 15 jobs reported; 200 matched loans coded NAICS 722410 *drinking places* | Snapshot from 2020-21; self-reported; only businesses that borrowed |
| 2 | **Bar vs restaurant classification** | Is this a restaurant or effectively a bar? GL class depends on alcohol share of receipts (e.g. 16910 under 30%, 16916 30-75%, 16920 75%+; [third-party listing](https://insurancexdate.com/class/NJ/OXJV/restaurant), confirm against ISO) | Licence type and class ([9s3h-dpkz](https://data.ny.gov/d/9s3h-dpkz)), OSM bar/pub category, PPP NAICS 722410, website drinks list | Licence classes on matched restaurants: 0340 (2,284), 0240 (869), 0370 (578), 0267 (262) | Dataset class codes need the SLA's code table to decode; the [SLA quick reference](https://sla.ny.gov/restaurant-license-quick-reference-0) names licence types (OP 252, RW 341, EB 141), not these codes |
| 3 | **Mid-term change alerts** | Has the risk changed since bind? | Health inspections ([43nn-pn8j](https://data.cityofnewyork.us/d/43nn-pn8j)), [SLA pending licences](https://data.ny.gov/d/f8i8-k2gm), [SLA inactive licences](https://data.ny.gov/d/6dg3-2z7i), DOB/ECB violations; all updated daily | 150 restaurants closed by the health department in the last 12 months; 608 pending licence applications; 10,396 inactive licence records | Alerts need a book of in-force policies to be useful |
| 4 | **Cooking fire controls** | Are kitchen fire protections in place? Cooking equipment causes about 61% of eating and drinking establishment fires ([NFPA 2010-14, via Ansul](https://www.ansul.com/Insights/Two-NFPA-Restaurant-Fire-Stats)) | FDNY summonses (already ingested), DOB NOW permits ([rbx6-tga4](https://data.cityofnewyork.us/d/rbx6-tga4), already downloaded, unused) | 700 extinguisher-related FDNY summonses on our restaurants; 44,099 permits mention kitchen, hood, exhaust or sprinkler work | FDNY summons feed's latest attributed date is Oct 2024; permits are building-level |
| 5 | **Operator network** | Does the same owner run other risky locations? | Licence legal names ([9s3h-dpkz](https://data.ny.gov/d/9s3h-dpkz)); NY company register ([n9v6-gdp6](https://data.ny.gov/d/n9v6-gdp6)) also lists chairman and registered agent | 771 restaurants belong to a legal entity holding 2+ NYC licences | Principal-level linking (chairman, agent) not yet tested |
| 6 | **Property hazard for BOP** | Flood and storm exposure of the premises | PLUTO flood flags `firm07_flag`, `pfirm15_flag` ([64uk-42ks](https://data.cityofnewyork.us/d/64uk-42ks)); [Hurricane Evacuation Zones](https://data.cityofnewyork.us/d/epne-qv9x) | **730** restaurants (6.9%) on lots in the FEMA 1% flood zone (2007 FIRM or 2015 preliminary FIRM) | Evacuation zones need a point-in-polygon step; not measured yet |
| 7 | Industry claim benchmark | What injuries does this industry produce in NYC? | [NY WCB assembled claims](https://data.ny.gov/d/jshw-gkgu) | 35,019 accommodation and food claims injured in New York County | **No employer name**: benchmark only, cannot be attributed to a business |

## Recommended order
1. **Extensions 1 and 2 together.** They check the two inputs that drive premium for a restaurant: its class and its size.
   Misclassification is the documented leakage ([Verisk: about 52% of small commercial records carry the wrong industry
   code](https://www.verisk.com/blog/the-race-to-zero-on-a-road-paved-with-quality-data/)), and New York's dram shop law
   makes alcohol service a liability driver ([NYSBA](https://nysba.org/events/dram-shop-liability-in-new-york/)).
2. **Extension 3** once a design partner provides in-force policies: it turns a one-time check into monitoring.
3. **Extensions 4, 6 and 5**: each adds one more fact to the existing profile with data already downloaded or one query away.

## Checked and not worth pursuing
- **News (GDELT):** no coverage of small restaurants in a 3-month test.
- **Glassdoor / LinkedIn:** scraping breaches their terms (LinkedIn won its case against hiQ in 2022).
- **Storing or scoring Google reviews:** prohibited by the Google Maps Platform terms; live display only.
- **Review text as a risk predictor:** in our earlier test, 311 complaints and violation text added no lift over inspection
  history for predicting the next inspection result.
