"""Valuation input custody, not an investment or arbitrary-code security claim."""
from copy import copy, deepcopy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
import json
import operator
import pickle
from uuid import UUID

from pydantic import BaseModel, ValidationError
import pytest

from decision_kernel.identity import canonical_hash, canonical_json
from decision_kernel.valuation import ValuationBasis, ValuationChangeReason

AT = datetime(2026, 10, 8, 0, 0, tzinfo=timezone.utc)
FIELDS = ('fundamental_inputs', 'valuation_parameter_inputs', 'capital_structure_inputs',
          'fx_inputs', 'other_explicit_inputs')


def inputs():
    return {'earnings': Decimal('100.00'), 'path': [{'amount': '2'}, '3'],
            'tuple': ({'amount': '4'},), 'unknown': None}


def make(**updates):
    return ValuationBasis(**{
        'id': UUID(int=1), 'research_snapshot_id': UUID(int=2), 'version': 1,
        'as_of_datetime': AT, 'valuation_horizon_date': date(2027, 10, 8),
        'valuation_method': 'synthetic-unit-test', 'model_version': 'v1', 'currency': 'CNY',
        **updates})


@pytest.mark.parametrize('field', FIELDS)
def test_external_aliases_cannot_change_frozen_inputs(field):
    original = inputs()
    value = make(**{field: original})
    frozen_hash, old_dump = canonical_hash(value), value.model_dump()
    original['earnings'] = Decimal('900')
    original['path'][0]['amount'] = '900'
    original['path'].append('900')
    original['tuple'][0]['amount'] = '900'
    assert canonical_hash(value) == frozen_hash and value.model_dump() == old_dump
    assert getattr(value, field) == inputs()


@pytest.mark.parametrize('field', FIELDS)
def test_empty_default_is_read_only(field):
    value = make()
    with pytest.raises(TypeError, match='read-only'):
        getattr(value, field)['added'] = 'not allowed'
    assert value.model_dump()[field] == {}


DICT_MUTATIONS = {
    'assign': lambda d: operator.setitem(d, 'earnings', '999'),
    'delete': lambda d: operator.delitem(d, 'earnings'),
    'clear': lambda d: d.clear(), 'pop': lambda d: d.pop('earnings'),
    'popitem': lambda d: d.popitem(), 'setdefault': lambda d: d.setdefault('new', '1'),
    'update': lambda d: d.update({'earnings': '999'}),
    'ior': lambda d: operator.ior(d, {'earnings': '999'}),
}


@pytest.mark.parametrize('mutation', DICT_MUTATIONS.values(), ids=DICT_MUTATIONS)
def test_dictionary_mutations_are_rejected_without_changing_identity(mutation):
    value = make(fundamental_inputs=inputs())
    old = canonical_hash(value)
    with pytest.raises(TypeError, match='read-only'):
        mutation(value.fundamental_inputs)
    assert canonical_hash(value) == old
    assert value.id == UUID(int=1) and value.version == 1


LIST_MUTATIONS = {
    'assign': lambda s: operator.setitem(s, 0, '999'),
    'slice': lambda s: operator.setitem(s, slice(None), []),
    'delete': lambda s: operator.delitem(s, 0),
    'append': lambda s: s.append('999'), 'clear': lambda s: s.clear(),
    'extend': lambda s: s.extend(['999']), 'insert': lambda s: s.insert(0, '999'),
    'pop': lambda s: s.pop(), 'remove': lambda s: s.remove('3'),
    'reverse': lambda s: s.reverse(), 'sort': lambda s: s.sort(key=str),
    'iadd': lambda s: operator.iadd(s, ['999']), 'imul': lambda s: operator.imul(s, 0),
}


@pytest.mark.parametrize('mutation', LIST_MUTATIONS.values(), ids=LIST_MUTATIONS)
def test_nested_list_mutations_reject(mutation):
    value = make(fundamental_inputs=inputs())
    old = canonical_hash(value)
    with pytest.raises(TypeError, match='read-only'):
        mutation(value.fundamental_inputs['path'])
    assert canonical_hash(value) == old


@pytest.mark.parametrize('key', ['path', 'tuple'])
def test_dictionary_inside_sequence_is_also_read_only(key):
    value = make(fundamental_inputs=inputs())
    with pytest.raises(TypeError, match='read-only'):
        value.fundamental_inputs[key][0]['amount'] = '999'
    assert value.fundamental_inputs == inputs()


@pytest.mark.parametrize('copier', [copy, deepcopy, lambda v: v.model_copy(),
                                  lambda v: v.model_copy(deep=True),
                                  lambda v: pickle.loads(pickle.dumps(v))])
def test_copy_and_pickle_preserve_custody_and_wire_shape(copier):
    value = make(fundamental_inputs=inputs())
    cloned = copier(value)
    assert canonical_json(cloned) == canonical_json(value)
    assert cloned.model_dump() == value.model_dump()
    with pytest.raises(TypeError, match='read-only'):
        cloned.fundamental_inputs['path'].append('999')


def test_export_is_editable_detached_and_keeps_python_container_types():
    value = make(fundamental_inputs=inputs())
    raw = value.model_dump(mode='python', round_trip=True)
    assert type(raw['fundamental_inputs']) is dict
    assert type(raw['fundamental_inputs']['path']) is list
    assert type(raw['fundamental_inputs']['path'][0]) is dict
    assert type(raw['fundamental_inputs']['tuple']) is tuple
    assert raw['fundamental_inputs']['earnings'] == Decimal('100.00')
    before = value.model_dump_json()
    raw['fundamental_inputs']['path'][0]['amount'] = '999'
    assert value.model_dump_json() == before
    restored = ValuationBasis.model_validate_json(before)
    assert canonical_hash(restored) == canonical_hash(value)
    with pytest.raises(TypeError):
        restored.fundamental_inputs['path'][0]['amount'] = '999'
    selected = value.model_dump(include={'fundamental_inputs': {'path': {0: {'amount'}}}})
    assert selected == {'fundamental_inputs': {'path': [{'amount': '2'}]}}


@pytest.mark.parametrize('deep', [False, True])
def test_model_copy_update_does_not_reintroduce_external_aliases(deep):
    value = make(fundamental_inputs=inputs())
    new_inputs = {'path': [{'amount': '200'}]}
    successor = value.model_copy(update={'id': UUID(int=3), 'version': 2,
        'supersedes_valuation_basis_id': value.id, 'fundamental_inputs': new_inputs,
        'declared_change_reasons': (ValuationChangeReason.FUNDAMENTAL_REVISION,)}, deep=deep)
    successor.validate_version_lineage()
    new_inputs['path'][0]['amount'] = '900'
    assert successor.fundamental_inputs['path'][0]['amount'] == '200'
    assert value.fundamental_inputs == inputs()
    with pytest.raises(TypeError):
        successor.fundamental_inputs['path'][0]['amount'] = '999'
    with pytest.raises(ValueError):
        value.model_copy(update={'fundamental_inputs': {'x': 1.2}})


def test_model_copy_is_not_automatic_lineage_acceptance():
    value = make()
    invalid = value.model_copy(update={'version': 2})
    with pytest.raises(ValueError, match='predecessor'):
        ValuationBasis.model_validate(invalid.model_dump())


def test_nested_model_becomes_its_detached_serialized_input_value():
    class DeclaredInput(BaseModel):
        amounts: list[str]
    model = DeclaredInput(amounts=['100'])
    value = make(fundamental_inputs={'declared': model})
    model.amounts.append('999')
    assert value.model_dump()['fundamental_inputs'] == {'declared': {'amounts': ['100']}}
    with pytest.raises(TypeError):
        value.fundamental_inputs['declared']['amounts'].append('999')


@pytest.mark.parametrize('bad', [1.2, {1}, frozenset({1}), bytearray(b'a'),
                               Decimal('NaN'), datetime(2026, 10, 8), object()])
def test_noncanonical_values_do_not_enter_a_frozen_mapping(bad):
    with pytest.raises((ValueError, TypeError)):
        make(fundamental_inputs={'value': bad})


def test_mutable_enum_is_not_assumed_immutable_because_it_is_hashable():
    class MutableEnum(Enum):
        DATA = {'mutable': ['100']}
    with pytest.raises(ValueError, match='immutable scalar'):
        make(fundamental_inputs={'enum': MutableEnum.DATA})


def test_scalar_enum_and_decimal_clock_identifiers_keep_serialized_meaning():
    class Label(Enum):
        DATA = 'declared'
    value = make(fundamental_inputs={'enum': Label.DATA, 'date': AT.date(),
        'clock': AT, 'id': UUID(int=4), 'amount': Decimal('1.2300'), 'bool': False})
    dumped = value.model_dump()
    assert dumped['fundamental_inputs']['enum'] is Label.DATA
    assert dumped['fundamental_inputs']['clock'] == AT
    assert json.loads(canonical_json(value))['fundamental_inputs']['amount'] == '1.2300'


def committed_package():
    from decision_kernel.research import ResearchSnapshot, ResearchStatus, Scenario
    from decision_kernel.research_commit import ResearchCommitPackage, research_commit_information_bundle_hash
    basis = make(fundamental_inputs=inputs())
    snapshot = ResearchSnapshot(id=UUID(int=2), ticker='SYNTHETIC', company_name='Fixture only',
        exchange='TEST', currency='CNY', created_at=AT, as_of_datetime=AT,
        valuation_horizon_date=basis.valuation_horizon_date, version=1, schema_version=2,
        status=ResearchStatus.REVIEW, core_thesis='Test arithmetic only',
        market_expectations_narrative='Synthetic expectation', model_risk_notes='Synthetic risk',
        thesis_invalidation=('Synthetic condition',), created_by='unit-test',
        valuation_bases=(basis,), scenarios=(Scenario(id=UUID(int=5), research_snapshot_id=UUID(int=2),
            name='synthetic-world', probability=Decimal('1'), terminal_equity_value_per_share=Decimal('120'),
            valuation_basis_id=basis.id),))
    snapshot = snapshot.model_copy(update={'information_bundle_hash': research_commit_information_bundle_hash(
        research_snapshot=snapshot, evidence_artifacts=())})
    return ResearchCommitPackage(research_snapshot=snapshot, proposed_committed_at=AT + timedelta(hours=1),
                                 schema_version=2)


def test_real_commit_and_calculation_consumers_keep_exact_snapshot_and_result():
    from decision_kernel.research_commit import commit_research_package
    from decision_kernel.calculation import calculate_research_economics, CalculationStatus
    from decision_kernel.market import ObservedMarket
    from decision_kernel.provisional_odds import HumanPriceContext, build_provisional_odds
    package = committed_package()
    result = commit_research_package(package)
    snapshot = result.research_snapshot
    market = ObservedMarket(market_price=Decimal('100'), market_timestamp=AT + timedelta(hours=2),
        market_utc_offset_minutes=0, market_data_source='synthetic-test',
        price_convention='synthetic close', currency='CNY')
    calculated_at = AT + timedelta(hours=3)
    before = canonical_hash(snapshot)
    calculation = calculate_research_economics(snapshot, market, created_at=calculated_at)
    assert calculation.status is CalculationStatus.CALCULATED
    assert calculation.aggregate.probability_weighted_undiscounted_holding_period_return == Decimal('.2')
    context = HumanPriceContext(ticker=snapshot.ticker, exchange=snapshot.exchange, currency='CNY',
        price=market.market_price, price_timestamp=market.market_timestamp, utc_offset_minutes=0,
        supplied_at=market.market_timestamp, source_reference='synthetic-human-context',
        price_convention='synthetic context')
    provisional = build_provisional_odds(research_snapshot=snapshot, price_context=context,
        artifact_id=UUID(int=6), created_at=calculated_at)
    with pytest.raises(TypeError):
        snapshot.valuation_bases[0].fundamental_inputs['path'][0]['amount'] = '999'
    assert canonical_hash(snapshot) == before
    assert calculate_research_economics(snapshot, market, created_at=calculated_at) == calculation
    assert build_provisional_odds(research_snapshot=snapshot, price_context=context,
        artifact_id=UUID(int=6), created_at=calculated_at) == provisional
    # Changing a detached candidate still needs the ORIGINAL package fingerprint.
    raw = package.model_dump()
    raw['research_snapshot']['valuation_bases'][0]['fundamental_inputs']['earnings'] = Decimal('999')
    from decision_kernel.research_commit import ResearchCommitPackage
    with pytest.raises(ValueError, match='information_bundle_hash'):
        commit_research_package(ResearchCommitPackage.model_validate(raw))
