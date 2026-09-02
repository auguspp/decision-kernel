from pathlib import Path

path = Path(__file__).with_name("generate_yto_v2_tmp.py")
source = path.read_text(encoding="utf-8")
old = '''s["valuation_bases"][0]["declared_change_reasons"] = [
    "Research v2 adds source-admissibility and expectation-event evidence; valuation parameters and scenario economics are unchanged."
]'''
new = '''s["valuation_bases"][0]["declared_change_reasons"] = ["OTHER_EXPLICIT"]'''
if old not in source:
    raise SystemExit("temporary generator patch target not found")
exec(compile(source.replace(old, new), str(path), "exec"))
