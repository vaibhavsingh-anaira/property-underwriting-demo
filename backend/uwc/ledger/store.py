"""Evidence ledger: bitemporal observations, location entities, documents.

Every fact is an Observation with a data-point type (C S N V D M R), a source
anchor, a valid-from date (when it was true) and a recorded-at date (when we
learned it). Nothing is overwritten; resolution picks a winner per field.
"""
from __future__ import annotations

import itertools
import json
import sqlite3
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from uwc.config import LEDGER_DB


@dataclass
class Obs:
    obs_id: str
    account_id: str
    subject_type: str            # account | location | policy | claim | recommendation
    subject_id: str
    field_code: str
    value: Any
    obs_type: str                # C S N V D M R
    source_family: str
    source_label: str
    recorded_at: str
    valid_from: str | None = None
    anchor: dict | None = None
    doc_id: str | None = None
    confidence: float = 0.95
    vendor: str | None = None
    model_version: str | None = None
    term: str | None = None      # prior | current | None
    verification_status: str = "UNVERIFIED"
    raw: Any = None              # raw value before normalisation (for N obs)


@dataclass
class LocationEntity:
    location_uid: str
    account_id: str
    label: str
    address: str
    city: str
    state: str
    zip: str | None = None
    lat: float | None = None
    lon: float | None = None
    geocode_level: str | None = None
    carrier_loc_id: str | None = None
    loc_no_prior: str | None = None
    loc_no_current: str | None = None
    in_prior: bool = False
    in_current: bool = False
    match_status: str = "MATCHED"     # MATCHED NEW DELETED SPLIT MERGED AMBIGUOUS
    match_method: str | None = None
    match_score: float | None = None
    match_confirmed_by: str | None = None
    merged_into: str | None = None
    merged_from: list[str] = field(default_factory=list)
    proposed_target: str | None = None
    aliases: list[dict] = field(default_factory=list)
    first_seen: str | None = None
    buildings_model_doc: str | None = None
    imagery_docs: list[str] = field(default_factory=list)


class Store:
    def __init__(self):
        self._seq = itertools.count(1)
        self.obs: dict[str, Obs] = {}
        self.by_subject: dict[tuple[str, str], list[str]] = {}         # (subject_id, field_code) -> obs ids
        self.by_account: dict[str, list[str]] = {}
        self.by_doc: dict[str, list[str]] = {}
        self.locations: dict[str, dict[str, LocationEntity]] = {}      # account -> uid -> entity
        self.docs: dict[str, dict] = {}                                 # received documents (registry rows)
        self.doc_issues: dict[str, list[dict]] = {}
        self.doc_method: dict[str, str] = {}

    # -------------------------------------------------------------- obs
    def add(self, **kw) -> Obs:
        oid = f"obs_{next(self._seq):06d}"
        o = Obs(obs_id=oid, **kw)
        self.obs[oid] = o
        self.by_subject.setdefault((o.subject_id, o.field_code), []).append(oid)
        self.by_account.setdefault(o.account_id, []).append(oid)
        if o.doc_id:
            self.by_doc.setdefault(o.doc_id, []).append(oid)
        return o

    def field_obs(self, subject_id: str, field_code: str, as_of: str | None = None, term: str | None = None) -> list[Obs]:
        ids = self.by_subject.get((subject_id, field_code), [])
        out = [self.obs[i] for i in ids]
        if as_of:
            out = [o for o in out if o.recorded_at <= as_of]
        if term:
            out = [o for o in out if o.term in (term, None)]
        return out

    def subject_fields(self, subject_id: str) -> list[str]:
        return sorted({f for (s, f) in self.by_subject if s == subject_id})

    def account_obs(self, account_id: str) -> Iterable[Obs]:
        return (self.obs[i] for i in self.by_account.get(account_id, []))

    def move_subject(self, from_uid: str, to_uid: str, label: str | None = None):
        """Re-point observations (used when a human confirms a proposed location match)."""
        for (s, f), ids in list(self.by_subject.items()):
            if s == from_uid:
                for i in ids:
                    self.obs[i].subject_id = to_uid
                self.by_subject.setdefault((to_uid, f), []).extend(ids)
                del self.by_subject[(s, f)]

    # -------------------------------------------------------------- locations
    def account_locations(self, account_id: str) -> dict[str, LocationEntity]:
        return self.locations.setdefault(account_id, {})

    def new_location_uid(self, account_id: str) -> str:
        n = len(self.account_locations(account_id)) + 1
        return f"{account_id}:loc{n:03d}"

    # -------------------------------------------------------------- persistence (inspection copy)
    def persist(self):
        LEDGER_DB.parent.mkdir(parents=True, exist_ok=True)
        if LEDGER_DB.exists():
            LEDGER_DB.unlink()
        con = sqlite3.connect(LEDGER_DB)
        con.execute("""create table observation (obs_id text primary key, account_id text, subject_type text, subject_id text,
            field_code text, value text, obs_type text, source_family text, source_label text, recorded_at text, valid_from text,
            anchor text, doc_id text, confidence real, vendor text, model_version text, term text, verification_status text)""")
        con.executemany("insert into observation values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [
            (o.obs_id, o.account_id, o.subject_type, o.subject_id, o.field_code, json.dumps(o.value, default=str), o.obs_type, o.source_family,
             o.source_label, o.recorded_at, o.valid_from, json.dumps(o.anchor), o.doc_id, o.confidence, o.vendor, o.model_version, o.term,
             o.verification_status) for o in self.obs.values()])
        con.execute("""create table location_entity (location_uid text primary key, account_id text, label text, address text, city text,
            state text, lat real, lon real, match_status text, match_method text, match_score real, carrier_loc_id text)""")
        con.executemany("insert into location_entity values (?,?,?,?,?,?,?,?,?,?,?,?)", [
            (l.location_uid, l.account_id, l.label, l.address, l.city, l.state, l.lat, l.lon, l.match_status, l.match_method, l.match_score, l.carrier_loc_id)
            for locs in self.locations.values() for l in locs.values()])
        con.execute("create index ix_obs_subject on observation(subject_id, field_code)")
        con.commit()
        con.close()


def obs_dict(o: Obs) -> dict:
    return asdict(o)
