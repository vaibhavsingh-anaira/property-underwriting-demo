# Pipeline evaluation

Generated 2026-10-13 04:27 UTC · scope: MANHATTAN · LLM: gemini-2.5-flash

All numbers are computed from real downloaded records; nothing is synthetic.

## 1. Sources ingested

| Source | Rows | Downloaded (UTC) | Dataset |
|---|---|---|---|
| inspections | 109,711 | 2026-10-12 14:20 | https://data.cityofnewyork.us/d/43nn-pn8j |
| liquor_licences | 24,818 | 2026-10-12 14:20 | https://data.ny.gov/d/9s3h-dpkz |
| complaints_311 | 125,844 | 2026-10-12 14:20 | https://data.cityofnewyork.us/d/erm2-nwe9 |
| pluto | 42,504 | 2026-10-12 14:21 | https://data.cityofnewyork.us/d/64uk-42ks |
| dob_violations | 918,678 | 2026-10-12 14:24 | https://data.cityofnewyork.us/d/3h2n-5cm9 |
| ecb_violations | 475,483 | 2026-10-12 14:25 | https://data.cityofnewyork.us/d/6bgk-3dad |
| dob_permits | 287,816 | 2026-10-12 14:26 | https://data.cityofnewyork.us/d/rbx6-tga4 |
| fdny_inspections | 168,195 | 2026-10-12 14:27 | https://data.cityofnewyork.us/d/kfgh-h6re |
| fire_summonses | 353,030 | 2026-10-12 14:28 | https://data.cityofnewyork.us/d/jz4z-kudi |
| dining_out | 1,583 | 2026-10-12 14:28 | https://data.cityofnewyork.us/d/fpeh-f7ci |
| osm | 11,178 | 2026-10-12 14:29 | OpenStreetMap Overpass API |

## 2. Entity resolution

Businesses in scope (inspected food establishments): **10,606**

| Source | Businesses linked | Share | Methods |
|---|---|---|---|
| osm | 4,771 | 45% | name+location |
| liquor_licences | 4,548 | 43% | name+address, exact name+location (200 m), name+location, address+shared name word |
| fire_summonses | 3,161 | 30% | respondent name+lot |
| dining_out | 1,269 | 12% | name+location, name+lot |

Businesses sharing a tax lot with another food business: 50%. Building-level records (violations, 311) for these lots cannot be attributed to one tenant and are labelled as building-level.

Legal names found in the NY company register: 3,331 of 5,047 (66%).

## 3. Websites

Sites fetched: 400 · usable (400+ words): 64% · needed headless rendering: 20% · blocked by robots.txt: 11%

## 4. LLM extraction

Prompt v2 · calls: 316 (316 succeeded) · tokens: 1,067,829 · page judged to be the business's own site: 92% · yes/no answers whose quote was found verbatim in the page: 87% (answers failing this check are discarded)

| Fact | yes | no | not stated |
|---|---|---|---|
| deep_frying | 38% | 1% | 61% |
| delivery | 59% | 1% | 40% |
| open_after_midnight | 21% | 43% | 36% |
| outdoor_seating | 7% | 0% | 93% |
| serves_alcohol | 39% | 2% | 59% |

## 5. Accuracy against official records

Truth for `serves_alcohol`: an active on-premises NYS liquor licence linked to the business. Licence matching itself misses some businesses, so a share of 'false positives' are real bars whose licence was not matched; they appear in the app as conflicts to review.

- Website + Gemini, all sites with a verdict: precision 89%, recall 56% (n=292; tp 101, fp 13, fn 78)
- Website + Gemini, only where the site states yes or no: precision 89%, recall 99% (n=120; tp 101, fp 13, fn 1)
- OpenStreetMap amenity=bar/pub, all linked venues: precision 90%, recall 22% (n=4,771; tp 548, fp 62, fn 1921)

## 6. Coverage and conflicts

| Fact | Businesses with a value | Share of 10,606 | Conflicts |
|---|---|---|---|
| building_active_ecb_violations | 10,555 | 100% | 0 |
| building_class | 10,514 | 99% | 0 |
| building_open_dob_violations | 10,555 | 100% | 0 |
| closures_3y | 10,606 | 100% | 0 |
| critical_violations_3y | 10,606 | 100% | 0 |
| deep_frying | 113 | 1% | 0 |
| delivery | 992 | 9% | 2 |
| entity_formed | 3,307 | 31% | 0 |
| fire_summonses | 3,161 | 30% | 0 |
| first_inspection | 10,606 | 100% | 0 |
| floors | 10,361 | 98% | 0 |
| last_grade | 10,606 | 100% | 0 |
| licence_first_issued | 4,548 | 43% | 0 |
| open_after_midnight | 3,469 | 33% | 60 |
| outdoor_seating | 1,932 | 18% | 14 |
| serves_alcohol | 10,606 | 100% | 74 |
| year_built | 10,384 | 98% | 0 |

Sample conflicts (each one is a question an underwriter would ask):

| Business | Address | Fact | Resolved | From | Disagreeing |
|---|---|---|---|---|---|
| DARBAR GRILL | 157 EAST   55 STREET | serves_alcohol | yes | Business website | NYS Liquor Authority=no |
| OBAO | 647 9 AVENUE | open_after_midnight | yes | Business website | OpenStreetMap=no |
| BROOKLYNEER | 220 WEST HOUSTON STREET | serves_alcohol | no | NYS Liquor Authority | OpenStreetMap=yes |
| FERRARA'S | 195 GRAND STREET | serves_alcohol | yes | Business website | NYS Liquor Authority=no |
| IHOP | 4168 BROADWAY | serves_alcohol | yes | Business website | NYS Liquor Authority=no |
| HARVEST KITCHEN | 269 COLUMBUS AVENUE | outdoor_seating | yes | NYC Dining Out licence | OpenStreetMap=no |
| TACO BELL | 1503 LEXINGTON AVENUE | open_after_midnight | yes | Business website | OpenStreetMap=no |
| MORTON'S THE STEAKHOUSE | 5 EAST   45 STREET | serves_alcohol | yes | Business website | NYS Liquor Authority=no |
| CAFE INTEGRAL | 149 ELIZABETH STREET | open_after_midnight | no | OpenStreetMap | NYC 311 complaints=yes |
| BANGIA | 11 EAST   32 STREET | serves_alcohol | yes | Business website | NYS Liquor Authority=no |
| 212 EAST | 212 EAST    9 STREET | serves_alcohol | no | NYS Liquor Authority | OpenStreetMap=yes |
| THE ROXY HOTEL / THE DJANGO / PAUL'S COCKTAIL LOUNGE | 32 WHITE STREET | serves_alcohol | yes | Business website | NYS Liquor Authority=no |
