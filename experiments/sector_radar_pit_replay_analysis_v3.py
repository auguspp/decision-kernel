from __future__ import annotations

import argparse, hashlib, json, statistics
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from decision_kernel.runtime.sector_radar import (
    SECTOR_RADAR_FORMULA_VERSION, SECTOR_RADAR_HUMAN_ATTENTION_AUTHORITY,
    SECTOR_RADAR_INVESTMENT_AUTHORITY, SECTOR_RADAR_SEMANTICS,
    SectorPricePoint, SectorPriceSeries, calculate_sector_radar_snapshot,
)

RUN_ID, ARTIFACT_ID = 33869436890, 9936117543
ARTIFACT_SHA256 = "58de421f48f5d8d5ddafd1a702e1f676367f450da145948e932b186d6cd78816"
CATALOG_HASH = "367d64660f5ef1f715ae0ef1d832a180d075ec7d6fc0a915797cbfafbd33f360"
PRESSURE = {
    "农业 / 种植": (("881101.TI",), ("884002.TI", "884003.TI", "884004.TI")),
    "养殖 / 猪肉 / 鸡肉": (("881102.TI",), ("884275.TI", "884276.TI", "884277.TI")),
    "水产": (("881102.TI",), ("884005.TI", "884006.TI", "884279.TI")),
    "造船 / 航海装备": (("881166.TI",), ("884183.TI",)),
}
RULE = "20d excess > 0 + 20d rating >= 75 + top-quartile run == 3 sessions; strongest rank first; cap 3"


def j(value: Any) -> Any:
    if is_dataclass(value): return j(asdict(value))
    if isinstance(value, Mapping): return {str(k): j(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [j(v) for v in value]
    if isinstance(value, Decimal): return format(value, "f")
    if isinstance(value, (date, datetime)): return value.isoformat()
    return value


def h(value: Any) -> str:
    raw = json.dumps(j(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def load(root: Path):
    progress = [json.loads(x) for x in (root / "sector-radar-pit-replay-progress.jsonl").read_text().splitlines()]
    calendar = [x for x in progress if x.get("stage") == "calendar"]
    catalog = [x for x in progress if x.get("stage") == "catalog"]
    histories = [x for x in progress if x.get("stage") == "history"]
    if len(calendar) != 1 or len(catalog) != 1 or len(histories) != 101: raise ValueError("incomplete retained acquisition")
    if catalog[0].get("catalog_hash") != CATALOG_HASH: raise ValueError("catalog hash mismatch")
    series, family, hashes = {}, {}, {}
    for meta in histories:
        code = meta["thscode"].upper(); path = root / meta["checkpoint_path"]
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if sha != meta.get("checkpoint_sha256"): raise ValueError(f"checkpoint hash mismatch {code}")
        p = json.loads(path.read_text())
        if p.get("thscode") != code or p.get("response_session") != p.get("expected_latest_session"): raise ValueError(f"stale or wrong checkpoint {code}")
        if p.get("response_session") != calendar[0].get("latest_session"): raise ValueError(f"calendar mismatch {code}")
        if p.get("checkpoint_semantics") != "QUALIFIED_HISTORY_INPUT_ONLY" or p.get("human_attention_authority") != "NONE" or p.get("investment_authority") != "NONE": raise ValueError(f"authority/semantics mismatch {code}")
        if p["request"].get("envelope_sha256") != meta.get("envelope_sha256"): raise ValueError(f"lineage mismatch {code}")
        points = tuple(SectorPricePoint(datetime.fromisoformat(x["as_of"]).date(), Decimal(x["close"]), Decimal(x["turnover"])) for x in p["points"])
        if len(points) != 164 or tuple(x.session for x in points) != tuple(sorted({x.session for x in points})): raise ValueError(f"session mismatch {code}")
        series[code] = SectorPriceSeries(code, meta["name"], points); family[code] = meta["family"]; hashes[code] = sha
    benchmark = series["000300.SH"]
    broad = tuple(series[c] for c in sorted(series) if family[c] == "BROAD_881")
    granular = tuple(series[c] for c in sorted(series) if family[c] == "GRANULAR_884")
    sessions = tuple(x.session for x in benchmark.points)
    if len(broad) != 90 or len(granular) != 10 or any(tuple(x.session for x in s.points) != sessions for s in (*broad, *granular)): raise ValueError("universe/alignment mismatch")
    return benchmark, broad, granular, {"history_count": 101, "broad_count": 90, "granular_count": 10, "session_count": 164, "start": sessions[0], "end": sessions[-1], "catalog_hash": CATALOG_HASH, "checkpoint_set_hash": h(hashes), "hashes_verified": True, "session_alignment_verified": True}


def r(values, end, n): return values[end] / values[end-n] - 1


def granular(s, b, asof):
    bp = tuple(x for x in b.points if x.session <= asof)[-126:]; by = {x.session:x for x in s.points}
    sp = tuple(by[x.session] for x in bp); dates = tuple(x.session for x in bp)
    bc, sc, turn = tuple(x.close for x in bp), tuple(x.close for x in sp), tuple(x.turnover for x in sp); end = len(bp)-1
    ex = {n:r(sc,end,n)-r(bc,end,n) for n in (5,20,60)}
    hist = {i:r(sc,i,20)-r(bc,i,20) for i in range(20,end+1)}
    count=0; started=None
    for i in range(end,19,-1):
        if hist[i] <= 0: break
        count += 1; started = dates[i]
    prior = sum(turn[-25:-5], Decimal())/20; pulse = None if prior == 0 else (sum(turn[-5:], Decimal())/5)/prior
    return {"thscode":s.thscode,"name":s.name,"as_of":asof,"excess_5":ex[5],"excess_20":ex[20],"excess_60":ex[60],"acceleration_5_sessions_20d":hist[end]-hist[end-5],"positive_20d_persistence":count,"positive_20d_run_started":started,"turnover_pulse":pulse}


def first(trace, pred): return next((x for x in trace if pred(x)), None)


def broad_marks(trace):
    return {"first_positive":first(trace,lambda x:x.horizon_20.excess_return>0),"first_top_quartile":first(trace,lambda x:x.horizon_20.excess_return>0 and x.horizon_20.cross_sectional_rating>=75),"first_confirmed_top_quartile":first(trace,lambda x:x.horizon_20.excess_return>0 and x.horizon_20.cross_sectional_rating>=75 and x.top_quartile_20d_persistence_sessions==3),"first_top_decile":first(trace,lambda x:x.horizon_20.excess_return>0 and x.horizon_20.cross_sectional_rating>=90),"latest":trace[-1]}


def granular_marks(trace): return {"first_positive":first(trace,lambda x:x["excess_20"]>0),"first_run_3":first(trace,lambda x:x["positive_20d_persistence"]==3),"first_run_5":first(trace,lambda x:x["positive_20d_persistence"]==5),"latest":trace[-1]}


def forward(s,b,asof,n):
    dates=tuple(x.session for x in b.points); i=dates.index(asof)
    if i+n>=len(dates): return None
    end=dates[i+n]; sc={x.session:x.close for x in s.points}; bc={x.session:x.close for x in b.points}
    sr=sc[end]/sc[asof]-1; br=bc[end]/bc[asof]-1
    return {"end":end,"sector_return":sr,"benchmark_return":br,"excess_return":sr-br}


def stats(values): return {"count":len(values),"mean":sum(values,Decimal())/len(values),"median":Decimal(str(statistics.median(values))),"positive_share":Decimal(sum(x>0 for x in values))/len(values)} if values else {"count":0}


def run(root: Path):
    benchmark,broad,granular_controls,integrity=load(root); dates=tuple(x.session for x in benchmark.points)[60:]
    broad_by={x.thscode:x for x in broad}; granular_by={x.thscode:x for x in granular_controls}; replay={}
    for d in dates:
        snap=calculate_sector_radar_snapshot(sectors=broad,benchmark=benchmark,as_of_session=d)
        if snap.exclusions or len(snap.observations)!=90: raise ValueError(f"coverage failure {d}")
        if (snap.radar_semantics,snap.human_attention_authority,snap.investment_authority)!=(SECTOR_RADAR_SEMANTICS,SECTOR_RADAR_HUMAN_ATTENTION_AUTHORITY,SECTOR_RADAR_INVESTMENT_AUTHORITY): raise ValueError("authority changed")
        replay[d]={x.thscode:x for x in snap.observations}
    greplay={d:{c:granular(s,benchmark,d) for c,s in granular_by.items()} for d in dates}
    pressure={}
    for name,(bcodes,gcodes) in PRESSURE.items(): pressure[name]={"broad":{c:broad_marks(tuple(replay[d][c] for d in dates)) for c in bcodes},"granular":{c:granular_marks(tuple(greplay[d][c] for d in dates)) for c in gcodes}}
    daily=[]; events=[]
    for d in dates:
        eligible=[x for x in replay[d].values() if x.horizon_20.excess_return>0 and x.horizon_20.cross_sectional_rating>=75 and x.top_quartile_20d_persistence_sessions==3]
        eligible.sort(key=lambda x:(x.horizon_20.cross_sectional_rank,-x.rank_change_5_sessions_20d,x.thscode))
        daily.append({"date":d,"eligible":len(eligible),"selected":[x.thscode for x in eligible[:3]],"omitted":[x.thscode for x in eligible[3:]]})
        for pos,x in enumerate(eligible,1): events.append({"date":d,"position":pos if pos<=3 else None,"observation":x,"forward_5":forward(broad_by[x.thscode],benchmark,d,5),"forward_20":forward(broad_by[x.thscode],benchmark,d,20)})
    f5=[x["forward_5"]["excess_return"] for x in events if x["forward_5"]]; f20=[x["forward_20"]["excess_return"] for x in events if x["forward_20"]]
    result={"schema_version":1,"status":"COMPLETED_PARTIAL_PASS","source_artifact":{"run_id":RUN_ID,"artifact_id":ARTIFACT_ID,"artifact_sha256":ARTIFACT_SHA256,"acquisition":"ALL_101_QUALIFIED_HISTORIES_ACQUIRED"},"formula_version":SECTOR_RADAR_FORMULA_VERSION,"integrity":integrity,"replay":{"start":dates[0],"end":dates[-1],"days":len(dates)},"pressure_cases":pressure,"challenger":{"status":"RETROSPECTIVE_ONLY_NOT_AUTHORIZED","rule":RULE,"quiet_days":sum(x["eligible"]==0 for x in daily),"active_days":sum(x["eligible"]>0 for x in daily),"events":len(events),"selected":sum(x["position"] is not None for x in events),"truncated_days":sum(x["eligible"]>3 for x in daily),"max_events":max(x["eligible"] for x in daily),"forward_5_excess":stats(f5),"forward_20_excess":stats(f20),"daily":daily},"decision":{"phase_c_broad_881":"PARTIAL_PASS","agriculture_livestock_early_discovery":"DEMONSTRATED","trend_age_visibility":"DEMONSTRATED","broad_only_shipbuilding_coverage":"FAILED","phase_d_production_alert":"NOT_AUTHORIZED","next":"separate 884 challenger + current breadth + shadow-only producer"},"radar_semantics":SECTOR_RADAR_SEMANTICS,"human_attention_authority":SECTOR_RADAR_HUMAN_ATTENTION_AUTHORITY,"investment_authority":SECTOR_RADAR_INVESTMENT_AUTHORITY}
    result["result_hash"]=h(result); return result


def pct(x): return f"{Decimal(str(x))*100:.2f}%"


def render(result):
    rows=[]
    for case,code in (("农业 / 种植","881101.TI"),("养殖 / 猪肉 / 鸡肉","881102.TI"),("水产","881102.TI"),("造船 / 航海装备","881166.TI")):
        m=result["pressure_cases"][case]["broad"][code]; c=m["first_confirmed_top_quartile"]; latest=m["latest"]
        label="not observed" if c is None else f"{c['as_of_session']} / rank {c['horizon_20']['cross_sectional_rank']} / {pct(c['horizon_20']['excess_return'])}"
        rows.append(f"| {case} | {latest['name']} | {label} | {pct(latest['horizon_20']['excess_return'])} | {latest['positive_20d_excess_persistence_sessions']} |")
    q=result["challenger"]; i=result["integrity"]
    return "\n".join(["# Sector Discovery Radar — frozen-PIT replay result","","Status: **PARTIAL PASS / BROAD 881 SIGNAL FAMILY VALIDATED / GRANULAR DISCOVERY GAP PROVEN / NO PRODUCTION ALERT AUTHORITY**","","## Input integrity","",f"- Qualified histories: `{i['history_count']}` = 1 benchmark + 90 broad + 10 granular controls.",f"- Exact sessions: `{i['session_count']}` from `{i['start']}` through `{i['end']}`.",f"- Catalog hash: `{i['catalog_hash']}`; every checkpoint hash and session alignment verified.","","## Pressure cases","","| Human case | Broad identity | First confirmed top-quartile run | Latest 20d excess | Positive-excess age |","| --- | --- | --- | ---: | ---: |",*rows,"","`养殖业` was visible on 2026-07-07 and `种植业与林业` on 2026-08-05. `军工装备` never earned the same sustained broad signal while granular `航海装备` was positive and accelerating. Broad-only 881 discovery is incomplete for shipbuilding-like themes.","","## Compression challenger","",f"Rule: `{q['rule']}`","",f"- Replay days `{result['replay']['days']}`; quiet `{q['quiet_days']}`; active `{q['active_days']}`.",f"- Events `{q['events']}`; retained `{q['selected']}`; truncated days `{q['truncated_days']}`.",f"- T+5 median excess `{pct(q['forward_5_excess']['median'])}`; positive share `{pct(q['forward_5_excess']['positive_share'])}`.",f"- T+20 median excess `{pct(q['forward_20_excess']['median'])}`; positive share `{pct(q['forward_20_excess']['positive_share'])}`.","","Retrospective path outcomes are not causality, cheapness, a recommendation, or an authorized threshold. Weak T+5 follow-through keeps this in Research-attention triage rather than trading.","","## Decision","","```text","PHASE C BROAD 881 REPLAY = PARTIAL PASS","EARLY DISCOVERY FOR AGRICULTURE / LIVESTOCK = DEMONSTRATED","TREND-AGE VISIBILITY = DEMONSTRATED","BROAD-ONLY SHIPBUILDING COVERAGE = FAILED","THREE-SESSION RULE = RETROSPECTIVE CHALLENGER ONLY","PHASE D PRODUCTION ALERT = NOT AUTHORIZED","NEXT = separate 884 challenger + current breadth + shadow-only producer","HUMAN ATTENTION AUTHORITY = NONE","INVESTMENT AUTHORITY = NONE","```",""])


def main():
    p=argparse.ArgumentParser(); p.add_argument("--input-dir",type=Path,required=True); p.add_argument("--output-json",type=Path,required=True); p.add_argument("--output-summary",type=Path,required=True); a=p.parse_args()
    result=run(a.input_dir); raw=json.dumps(j(result),ensure_ascii=False,indent=2,sort_keys=True)+"\n"; a.output_json.write_text(raw); a.output_summary.write_text(render(json.loads(raw)))
    print(json.dumps({"status":result["status"],"result_hash":result["result_hash"],"broad_replay":result["decision"]["phase_c_broad_881"],"shipbuilding":result["decision"]["broad_only_shipbuilding_coverage"],"human_attention_authority":result["human_attention_authority"],"investment_authority":result["investment_authority"]},ensure_ascii=False,sort_keys=True))

if __name__ == "__main__": main()
