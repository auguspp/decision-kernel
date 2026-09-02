from pathlib import Path

path = Path(__file__).with_name("generate_yto_v2_tmp.py")
source = path.read_text(encoding="utf-8")

old_reason = '''s["valuation_bases"][0]["declared_change_reasons"] = [
    "Research v2 adds source-admissibility and expectation-event evidence; valuation parameters and scenario economics are unchanged."
]'''
new_reason = '''s["valuation_bases"][0]["declared_change_reasons"] = ["OTHER_EXPLICIT"]'''

old_contract = '''contract_base = deepcopy(V1_CONTRACT)'''
new_contract = '''contract_base = deepcopy(V1_CONTRACT)
contract_base.pop("schema_version", None)'''

if old_reason not in source or old_contract not in source:
    raise SystemExit("temporary generator patch target not found")
patched = source.replace(old_reason, new_reason).replace(old_contract, new_contract)
exec(compile(patched, str(path), "exec"))
