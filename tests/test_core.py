import pandas as pd
from smbv import normalize as N
from smbv.extract import verified
from smbv.ledger import resolve


def test_street_and_house():
    assert N.street("EAST 20 STREET") == N.street("E 20th St")
    assert N.street("THIRD AVENUE") == N.street("3rd Ave")
    assert N.split_address("105-45 CROSS BAY BLVD") == ("105", "CROSS BAY BLVD")


def test_name_drops_legal_suffixes():
    assert N.name("Little Poland LLC") == N.name("LITTLE POLAND")
    assert N.name("Smith & Wollensky") == "SMITH WOLLENSKY"


def test_closes_after_midnight():
    assert N.closes_after_midnight("Mo-Su 17:00-02:00") is True
    assert N.closes_after_midnight("Mo-Fr 11:00-22:00") is False
    assert N.closes_after_midnight("Fr,Sa 18:00-24:00") is True
    assert N.closes_after_midnight("24/7") is True
    assert N.closes_after_midnight("sunrise-sunset") is None


def test_quote_must_be_verbatim():
    page = "Our Cocktails:  Negroni $16 — Wine by the glass available."
    assert verified("Negroni $16", page)
    assert verified("wine by the glass", page)
    assert not verified("full bar with 40 beers on tap", page)


def test_resolution_prefers_trust_and_flags_conflict():
    obs = pd.DataFrame([
        {"business_id": "1", "fact": "serves_alcohol", "value": "no", "source": "licence absent", "trust": 1.5},
        {"business_id": "1", "fact": "serves_alcohol", "value": "yes", "source": "website", "trust": 2},
        {"business_id": "2", "fact": "serves_alcohol", "value": "yes", "source": "licence", "trust": 3},
        {"business_id": "2", "fact": "serves_alcohol", "value": "yes", "source": "osm", "trust": 1},
    ])
    f = resolve(obs).set_index("business_id")
    assert f.loc["1", "value"] == "yes" and bool(f.loc["1", "conflict"])
    assert f.loc["2", "value"] == "yes" and not bool(f.loc["2", "conflict"])


def test_generic_words_alone_do_not_match():
    from smbv.link import _score
    assert _score(N.name("DA BAO BAKERY"), N.name("E-BAKERY INC.")) < 80
    assert _score(N.name("Little Poland"), N.name("LITTLE POLAND LLC")) >= 90
    assert _score(N.name("RED EYE GRILL"), N.name("RED EYE GRILL")) == 100


def test_prompt_requires_explicit_no():
    from smbv.extract import prompt
    p = prompt("X", "1 Main St", "menu")
    assert "never \"no\"" in p and "BYOB" in p


def test_address_ranges():
    assert N.split_address("175 179 W 4TH STREET") == ("175", "W 4 ST")
    assert N.split_address("54 56 GANSEVOORT ST") == ("54", "GANSEVOORT ST")
    assert N.split_address("45 1 AVENUE") == ("45", "1 AVE")


def test_point_parsing():
    assert N.lon_lat("POINT (-73.88 40.86)") == (-73.88, 40.86)
    assert N.lon_lat("{'type': 'Point', 'coordinates': [-73.88474, 40.73203]}") == (-73.88474, 40.73203)
    assert N.lon_lat(None) == (None, None)


def test_bbl_formats():
    assert N.bbl("1020660059.00000000") == "1020660059"
    assert N.bbl("1008800050") == "1008800050"
    assert N.bbl(None) is None and N.bbl("0") is None
