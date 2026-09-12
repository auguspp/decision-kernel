from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"expected one match in {path}: {old[:80]!r}; got {text.count(old)}")
    p.write_text(text.replace(old, new), encoding="utf-8")


# 1) Reuse the existing Stock observer/gates with a second exact plan contract.
path = "src/decision_kernel/runtime/stock_radar_reading.py"
replace_once(path, "}\nLIMITS = {\n", "}\nMARKET_EXPRESSION_VERSION = 'stock-market-expression-window-qualified-v7'\nMARKET_EXPRESSION_SEMANTICS = 'BOUNDED_MARKET_EXPRESSION_NOT_BUSINESS_BENEFIT_OR_RECOMMENDATION'\nMARKET_EXPRESSION_POLICY = {\n    **POLICY,\n    'version': MARKET_EXPRESSION_VERSION,\n    'issuer_universe': 'BOUNDED_SURFACED_SECTOR_BREADTH_LEADERS_NOT_ALL_A_SHARES',\n    'business_evidence': 'ANNOTATION_ONLY_NOT_CANDIDATE_GATE',\n    'presentation': 'SURFACED_GROUP_ROUND_ROBIN_CANDIDATES_THEN_EXISTING_STOCK_GATE',\n}\nLIMITS = {\n")
replace_once(path,
"    'BUSINESS_COVERAGE_INSUFFICIENT': '有活跃方向，但没有相应已接入公司依据',\n",
"    'BUSINESS_COVERAGE_INSUFFICIENT': '有活跃方向，但没有相应已接入公司依据',\n    'NO_SURFACED_SECTOR_GROUPS': 'Sector 本轮没有进入首页有界组；未执行股票市场表达候选',\n    'NO_MARKET_EXPRESSION_CANDIDATES': 'Sector 有界组没有可路由的 breadth leader 候选',\n    'NO_MATCH_WITHIN_BOUNDED_MARKET_EXPRESSION_SCOPE': '本次有界市场表达候选没有通过全部价格观察条件',\n")
replace_once(path,
"def observe_stock_reading(plan: dict, state, *, request_json, observed_at: datetime,\n                          cutoff_clock=None, reference_inputs=None) -> dict:\n",
"def _plan_contract(plan: dict):\n    if plan.get('version') == VERSION:\n        return SEMANTICS, POLICY, False\n    if plan.get('version') == MARKET_EXPRESSION_VERSION:\n        return MARKET_EXPRESSION_SEMANTICS, MARKET_EXPRESSION_POLICY, True\n    return None\n\n\ndef observe_stock_reading(plan: dict, state, *, request_json, observed_at: datetime,\n                          cutoff_clock=None, reference_inputs=None) -> dict:\n")
replace_once(path,
"    if (plan['version'] != VERSION or plan['policy'] != POLICY or not _hash_ok(plan, 'plan_hash')\n            or plan['market_state_hash'] != state.state_hash or plan['semantics'] != SEMANTICS\n            or any(plan[k] != v for k, v in LIMITS.items())\n            or len(plan['issuers']) > MAX_ISSUERS or len(plan['directions']) > MAX_MEMBERSHIPS\n            or expected_requests != plan['maximum_request_count'] or expected_requests > MAX_REQUESTS):\n        raise ValueError('stock plan identity, policy, budget or authority differs')\n",
"    contract = _plan_contract(plan)\n    if contract is None:\n        raise ValueError('stock plan identity, policy, budget or authority differs')\n    contract_semantics, contract_policy, is_market_expression = contract\n    if (plan['policy'] != contract_policy or not _hash_ok(plan, 'plan_hash')\n            or plan['market_state_hash'] != state.state_hash or plan['semantics'] != contract_semantics\n            or any(plan[k] != v for k, v in LIMITS.items())\n            or len(plan['issuers']) > MAX_ISSUERS or len(plan['directions']) > MAX_MEMBERSHIPS\n            or expected_requests != plan['maximum_request_count'] or expected_requests > MAX_REQUESTS):\n        raise ValueError('stock plan identity, policy, budget or authority differs')\n")
replace_once(path,
"        row = {**issuer, 'current_origins': valid_origins, 'stock_path': None,\n               'market_comparison': {}, 'sector_comparisons': [], 'eligible_nodes': [],\n               'excluded_reasons': [], 'eligible_for_shadow_reading': False,\n               'status': 'CONDITIONS_NOT_MET', 'input_failure': None}\n        if not valid_origins:\n            row['excluded_reasons'].append('NOT_A_CURRENT_MEMBER_OF_REVIEWED_ACTIVE_DIRECTION')\n",
"        row = {**issuer, 'current_origins': valid_origins, 'stock_path': None,\n               'market_comparison': {}, 'sector_comparisons': [], 'eligible_nodes': [],\n               'excluded_reasons': [], 'eligible_for_shadow_reading': False,\n               'market_expression_status': 'NOT_ESTABLISHED',\n               'business_linkage_status': issuer.get('business_linkage_status', 'REVIEWED_BUSINESS_LINK_PRESENT'),\n               'business_benefit_status': issuer.get('business_benefit_status', 'NOT_ESTABLISHED'),\n               'status': 'CONDITIONS_NOT_MET', 'input_failure': None}\n        if not valid_origins:\n            row['excluded_reasons'].append('NOT_A_CURRENT_MEMBER_OF_ROUTED_ACTIVE_DIRECTION' if is_market_expression\n                                           else 'NOT_A_CURRENT_MEMBER_OF_REVIEWED_ACTIVE_DIRECTION')\n")
replace_once(path,
"        row['eligible_for_shadow_reading'] = not reasons\n        row['status'] = ('QUALIFIED_SYNTHETIC_READING' if reference_inputs is not None else\n                         'CONTRACT_CHECKED_RAW_READING') if not reasons else 'CONDITIONS_NOT_MET'\n",
"        row['eligible_for_shadow_reading'] = not reasons\n        if is_market_expression and not reasons:\n            row['market_expression_status'] = 'OBSERVED'\n        row['status'] = ('QUALIFIED_SYNTHETIC_READING' if reference_inputs is not None else\n                         'CONTRACT_CHECKED_RAW_READING') if not reasons else 'CONDITIONS_NOT_MET'\n")
replace_once(path,
"    reviewed_codes = {r['thscode'] for r in plan['issuers']}\n    status = _partial_status(coverage, selected) or (\n        'STOCKS_FOR_SHADOW_READING' if selected else\n        'NO_ACTIVE_DIRECTIONS' if not plan['all_active_direction_count'] else\n        'BUSINESS_COVERAGE_INSUFFICIENT' if not plan['issuers'] else\n        'NO_MATCH_WITHIN_REVIEWED_COMPANY_SCOPE')\n    payload = {\n        'version': VERSION, 'semantics': SEMANTICS, 'policy': POLICY, 'plan_hash': plan['plan_hash'],\n        'market_session': state.sessions[-1], 'observed_at': at(), 'status': status,\n        'scope': plan['reviewed_company_coverage'], 'reviewed_issuers': len(plan['issuers']),\n",
"    reviewed_codes = {r['thscode'] for r in (plan['evidence_scope_issuers'] if is_market_expression else plan['issuers'])}\n    if is_market_expression:\n        complete_status = ('STOCKS_FOR_SHADOW_READING' if selected else\n            'NO_SURFACED_SECTOR_GROUPS' if not plan['candidate_source_group_count'] else\n            'NO_MARKET_EXPRESSION_CANDIDATES' if not plan['issuers'] else\n            'NO_MATCH_WITHIN_BOUNDED_MARKET_EXPRESSION_SCOPE')\n    else:\n        complete_status = ('STOCKS_FOR_SHADOW_READING' if selected else\n            'NO_ACTIVE_DIRECTIONS' if not plan['all_active_direction_count'] else\n            'BUSINESS_COVERAGE_INSUFFICIENT' if not plan['issuers'] else\n            'NO_MATCH_WITHIN_REVIEWED_COMPANY_SCOPE')\n    status = _partial_status(coverage, selected) or complete_status\n    payload = {\n        'version': plan['version'], 'semantics': plan['semantics'], 'policy': plan['policy'], 'plan_hash': plan['plan_hash'],\n        'market_session': state.sessions[-1], 'observed_at': at(), 'status': status,\n        'scope': plan.get('reading_scope', plan['reviewed_company_coverage']),\n        'reviewed_issuers': (sum(r.get('business_linkage_status') == 'REVIEWED_BUSINESS_LINK_PRESENT' for r in plan['issuers'])\n                             if is_market_expression else len(plan['issuers'])),\n")
replace_once(path,
"        'profitability_valuation_or_odds_established': False, **LIMITS,\n    }\n",
"        'profitability_valuation_or_odds_established': False, **LIMITS,\n        **({'sector_result_hash': plan['sector_result_hash'],\n            'candidate_source_group_count': plan['candidate_source_group_count'],\n            'candidate_routing': plan['candidate_routing']} if is_market_expression else {}),\n    }\n")

# 2) Live capture binds and retains the exact Sector result; legacy library callers still work.
path = ".github/scripts/capture-stock-reading.py"
replace_once(path,
"from decision_kernel.runtime import stock_radar_reading as stock\n",
"from decision_kernel.runtime import stock_radar_reading as stock\nfrom decision_kernel.runtime import stock_market_expression as market_expression\n")
replace_once(path, "VERSION = 'stock-reading-capture-replay-v6'\n", "VERSION = 'stock-reading-capture-replay-v7'\n")
replace_once(path,
"def load_inputs(root, at, *, company_manifest=stock.COMPANY_MANIFEST):\n",
"def load_inputs(root, at, *, company_manifest=stock.COMPANY_MANIFEST, sector_result=None):\n")
replace_once(path,
"    plan = stock.prepare_stock_reading(root,bundle.market_state,bundle.event_ledger,association,\n        observed_at=at,company_manifest=company_manifest)\n",
"    plan = (market_expression.prepare_market_expression_reading(\n        root,bundle.market_state,bundle.event_ledger,association,sector_result,\n        observed_at=at,company_manifest=company_manifest) if sector_result is not None else\n        stock.prepare_stock_reading(root,bundle.market_state,bundle.event_ledger,association,\n            observed_at=at,company_manifest=company_manifest))\n")
replace_once(path,
"def page(report, provenance):\n    result = stock.render_stock_reading(report)\n",
"def page(report, provenance):\n    result = (market_expression.render_market_expression_reading(report)\n              if report['projection']['version'] == stock.MARKET_EXPRESSION_VERSION\n              else stock.render_stock_reading(report))\n")
replace_once(path,
"def capture(source_root, state_dir, output, *, observed_at, transport, workflow,\n            provenance=SYNTHETIC, credential='', now=lambda:datetime.now(timezone.utc),\n            pause=time.sleep, reference_inputs=None, company_manifest=stock.COMPANY_MANIFEST):\n",
"def capture(source_root, state_dir, output, *, observed_at, transport, workflow,\n            provenance=SYNTHETIC, credential='', now=lambda:datetime.now(timezone.utc),\n            pause=time.sleep, reference_inputs=None, company_manifest=stock.COMPANY_MANIFEST,\n            sector_result=None):\n")
replace_once(path,
"    for name, raw in files.items():\n        p=output/'inputs'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)\n    if reference_inputs is not None:\n",
"    for name, raw in files.items():\n        p=output/'inputs'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)\n    if sector_result is not None:\n        write(output/'inputs/sector-result.json', sector_result)\n    if reference_inputs is not None:\n")
replace_once(path,
"        bundle, association, plan = load_inputs(output/'inputs',observed_at,company_manifest=company_manifest)\n",
"        copied_sector = read(output/'inputs/sector-result.json') if (output/'inputs/sector-result.json').exists() else None\n        bundle, association, plan = load_inputs(output/'inputs',observed_at,company_manifest=company_manifest,\n            sector_result=copied_sector)\n")
replace_once(path,
"    bundle,association,plan=load_inputs(output/'inputs',at,company_manifest=company_manifest)\n",
"    sector_path=output/'inputs/sector-result.json'\n    sector_result=read(sector_path) if sector_path.exists() else None\n    bundle,association,plan=load_inputs(output/'inputs',at,company_manifest=company_manifest,sector_result=sector_result)\n")
replace_once(path,
"        '<p>只限已接入公司依据及其活跃方向，不是全A股盲筛。后续未完成项不视为条件不满足；之前已取得的输入也不冒充完整筛选。</p>'\n",
"        '<p>只处理本次显式有界范围，不是全A股盲筛。Business Evidence 不由成员身份或价格补写；后续未完成项不视为条件不满足。</p>'\n")
# Exact sibling full artifact binding from the same already-qualified Sector run.
replace_once(path,
"def binding(root, request):\n    return sibling('native-feed-acceptance.py')['metadata'](request,'market',read(root/'market-run.json'),read(root/'market-artifacts.json'))\n\n\ndef bound_state(root, request):\n",
"def binding(root, request):\n    return sibling('native-feed-acceptance.py')['metadata'](request,'market',read(root/'market-run.json'),read(root/'market-artifacts.json'))\n\n\ndef context_binding(root, request):\n    state_bound = binding(root, request)\n    run, listing = read(root/'market-run.json'), read(root/'market-artifacts.json')\n    at = probe._clock(request['prepared_at'])\n    if type(listing['total_count']) is not int or listing['total_count'] != len(listing['artifacts']):\n        raise ValueError('complete market artifact listing required')\n    name = 'sector-radar-run-' + request['market_run_id']\n    matches = [a for a in listing['artifacts'] if a['name'] == name]\n    if len(matches) != 1:\n        raise ValueError('one exact Sector run artifact required')\n    a = matches[0]; relation = a['workflow_run']\n    if (type(a['id']) is not int or a['expired'] is not False\n            or type(a['size_in_bytes']) is not int or not 0 < a['size_in_bytes'] <= 32*1024*1024\n            or relation['id'] != run['id'] or relation['head_sha'] != run['head_sha']\n            or relation['head_branch'] != 'main' or relation['repository_id'] != run['repository']['id']\n            or relation['head_repository_id'] != run['repository']['id']\n            or probe._clock(a['expires_at']) <= at\n            or not isinstance(a['digest'], str) or not a['digest'].startswith('sha256:')):\n        raise ValueError('Sector run artifact identity or retention differs')\n    helper=sibling('prepare-native-rss-successor.py')\n    helper['number'](str(a['id']));helper['hash_value'](a['digest'][7:])\n    return {'kind':'market-context','run_id':request['market_run_id'],'commit':run['head_sha'],\n            'artifact_id':str(a['id']),'artifact_digest':a['digest'],\n            'state_artifact_id':state_bound['artifact_id'],'request_hash':canonical_hash(request)}\n\n\ndef bound_state(root, request):\n")
replace_once(path,
"    bound=binding(root,request)\n    if bound!=read(root/'market-binding.json'):raise ValueError('market binding changed')\n    helper=sibling('build-sector-radar-reading.py')\n",
"    bound=binding(root,request)\n    if bound!=read(root/'market-binding.json'):raise ValueError('market binding changed')\n    context=context_binding(root,request)\n    if context!=read(root/'market-context-binding.json'):raise ValueError('market context binding changed')\n    helper=sibling('build-sector-radar-reading.py')\n")
replace_once(path,
"    if str(m.source_run_id)!=bound['run_id'] or m.source_commit_sha!=bound['commit'] or m.source_run_attempt!=1:\n        raise ValueError('state does not identify selected successful remote run')\n    return b\n",
"    if str(m.source_run_id)!=bound['run_id'] or m.source_commit_sha!=bound['commit'] or m.source_run_attempt!=1:\n        raise ValueError('state does not identify selected successful remote run')\n    identity={'repository':'auguspp/decision-kernel','workflow_path':'.github/workflows/sector-radar-shadow.yml',\n              'run_id':int(bound['run_id']),'run_attempt':1,'commit_sha':bound['commit']}\n    helper['_check_run'](root/'market-context',root/'market',identity)\n    return b\n")
replace_once(path,
"            if args.mode=='metadata':\n                value=binding(root,request);write(root/'market-binding.json',value)\n                with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('artifact_id='+value['artifact_id']+'\\n')\n",
"            if args.mode=='metadata':\n                value=binding(root,request);context=context_binding(root,request)\n                write(root/'market-binding.json',value);write(root/'market-context-binding.json',context)\n                with open(os.environ['GITHUB_OUTPUT'],'a') as f:\n                    f.write('artifact_id='+value['artifact_id']+'\\ncontext_artifact_id='+context['artifact_id']+'\\n')\n")
replace_once(path,
"                    value=capture(Path(os.environ['GITHUB_WORKSPACE']),root/'market',root/'reading',\n                        observed_at=datetime.now(timezone.utc),workflow=request['workflow'],provenance=PUBLIC,credential=key,\n                        company_manifest=LIVE_COMPANIES,\n                        transport=lambda p,q:hithink_stock_reading.request_json(api_key=key,path=p,params=q))\n",
"                    sector_result=read(root/'market-context/result.json')\n                    value=capture(Path(os.environ['GITHUB_WORKSPACE']),root/'market',root/'reading',\n                        observed_at=datetime.now(timezone.utc),workflow=request['workflow'],provenance=PUBLIC,credential=key,\n                        company_manifest=LIVE_COMPANIES,sector_result=sector_result,\n                        transport=lambda p,q:hithink_stock_reading.request_json(api_key=key,path=p,params=q))\n")

# 3) Download the second exact artifact; still the same selected Sector run.
path = ".github/workflows/hithink-stock-dump-trial.yml"
replace_once(path,
"      - name: Build stock-first observations\n",
"      - name: Download exact read-only Sector result context\n        uses: actions/download-artifact@v8\n        with:\n          artifact-ids: ${{ steps.stock-state.outputs.context_artifact_id }}\n          run-id: ${{ steps.stock-intent.outputs.market_run_id }}\n          repository: auguspp/decision-kernel\n          github-token: ${{ github.token }}\n          digest-mismatch: error\n          path: ${{ runner.temp }}/stock-reading-run/market-context\n      - name: Build stock-first observations\n")
replace_once(path,
"              lines += [f\"行情交易日 {p['market_session']}；已接入业务依据范围内 {len(p['surfaced_stocks'])} 只通过观察条件。\"]\n",
"              lines += [f\"行情交易日 {p['market_session']}；本次有界 Market Expression 范围内 {len(p['surfaced_stocks'])} 只通过观察条件。\"]\n")
replace_once(path,
"              lines += [f\"审阅公司 {p['reviewed_issuers']}；未接入业务依据的当前成员 {len(p['unreviewed_current_members'])}；不是全 A 股盲选。\",\n",
"              lines += [f\"计划候选 {c['planned_issuers']}；其中 exact reviewed business link {p['reviewed_issuers']}；Business Evidence 不是候选门槛；不是全 A 股盲选。\",\n")

# 4) Current-state accepts both legacy v6 and v7, and checks exact copied Sector result binding.
path = "src/decision_kernel/runtime/current_state.py"
replace_once(path,
"def validate_stock(run: dict, files: dict[str, bytes]) -> dict:\n    from .stock_radar_reading import render_stock_reading, HITHINK_RAW\n",
"def validate_stock(run: dict, files: dict[str, bytes]) -> dict:\n    from . import stock_radar_reading as stock\n    from .stock_market_expression import render_market_expression_reading\n    HITHINK_RAW = stock.HITHINK_RAW\n")
replace_once(path,
"    report = json.loads(files[\"reading/stock-reading.json\"])\n    render_stock_reading(report)  # Existing pure validator/renderer, not live CLI/selector.\n    p = report[\"projection\"]\n",
"    report = json.loads(files[\"reading/stock-reading.json\"])\n    p = report[\"projection\"]\n    if p.get('version') == stock.MARKET_EXPRESSION_VERSION:\n        render_market_expression_reading(report)\n    else:\n        stock.render_stock_reading(report)\n")
replace_once(path,
"    binding = json.loads(files[\"market-binding.json\"])\n    check(binding[\"request_hash\"] == canonical_hash(request)\n          and str(binding[\"run_id\"]) == str(request[\"market_run_id\"]) == str(market_manifest[\"source_run_id\"])\n          and binding[\"commit\"] == market_manifest[\"source_commit_sha\"], \"stock exact market request differs\")\n",
"    binding = json.loads(files[\"market-binding.json\"])\n    check(binding[\"request_hash\"] == canonical_hash(request)\n          and str(binding[\"run_id\"]) == str(request[\"market_run_id\"]) == str(market_manifest[\"source_run_id\"])\n          and binding[\"commit\"] == market_manifest[\"source_commit_sha\"], \"stock exact market request differs\")\n    if p.get('version') == stock.MARKET_EXPRESSION_VERSION:\n        context_binding = json.loads(files[\"market-context-binding.json\"])\n        sector_raw = files[\"reading/inputs/sector-result.json\"]\n        check(files[\"market-context/result.json\"] == sector_raw, \"Stock Sector result copy differs from exact bound run artifact\")\n        sector_result = json.loads(sector_raw)\n        check(context_binding[\"request_hash\"] == binding[\"request_hash\"]\n              and context_binding[\"run_id\"] == binding[\"run_id\"]\n              and context_binding[\"commit\"] == binding[\"commit\"]\n              and context_binding[\"state_artifact_id\"] == binding[\"artifact_id\"]\n              and sector_result[\"result_hash\"] == p[\"sector_result_hash\"]\n              and sector_result[\"output_market_state_hash\"] == p[\"market_state_hash\"]\n              and sector_result[\"event_ledger_update\"][\"event_ledger_hash\"] == p[\"event_ledger_hash\"],\n              \"Stock market-expression Sector result binding differs\")\n")
replace_once(path,
"            \"dispositions\": [{\"thscode\": r[\"thscode\"], \"company_name\": r[\"company_name\"],\n                              \"status\": r[\"status\"], \"excluded_reasons\": r[\"excluded_reasons\"],\n                              \"input_failure\": r[\"input_failure\"]} for r in p[\"all_stock_observations\"]],\n",
"            \"dispositions\": [{\"thscode\": r[\"thscode\"], \"company_name\": r[\"company_name\"],\n                              \"status\": r[\"status\"], \"excluded_reasons\": r[\"excluded_reasons\"],\n                              \"input_failure\": r[\"input_failure\"],\n                              \"market_expression_status\": r.get(\"market_expression_status\"),\n                              \"business_linkage_status\": r.get(\"business_linkage_status\"),\n                              \"business_benefit_status\": r.get(\"business_benefit_status\")}\n                             for r in p[\"all_stock_observations\"]],\n")

path = "src/decision_kernel/runtime/current_state_delivery.py"
replace_once(path,
"            details = {n: self.retain(prefix + n, files[n]) for n in (\n                \"reading/stock-reading.json\", \"reading/index.html\", \"verification.json\", \"market-binding.json\")}\n",
"            names = [\"reading/stock-reading.json\", \"reading/index.html\", \"verification.json\", \"market-binding.json\"]\n            if \"market-context-binding.json\" in files:\n                names += [\"market-context-binding.json\", \"reading/inputs/sector-result.json\"]\n            details = {n: self.retain(prefix + n, files[n]) for n in names}\n")

print('P0 market-expression patch applied')
