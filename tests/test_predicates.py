from chaoschain.schemas.predicates import is_valid_predicate, parse_predicate


def test_valid_three_part():
    cls, obj, op, mod = parse_predicate("app_resource.connection_pool.exhausted")
    assert cls == "app_resource"
    assert obj == "connection_pool"
    assert op == "exhausted"
    assert mod is None


def test_valid_with_modifier():
    _, _, _, mod = parse_predicate("compute.memory.leaked.slow")
    assert mod == "slow"


def test_invalid_class():
    assert not is_valid_predicate("nonsense.foo.exhausted")


def test_invalid_op():
    assert not is_valid_predicate("compute.memory.banana")


def test_too_few_parts():
    assert not is_valid_predicate("compute.memory")


def test_empty_object():
    assert not is_valid_predicate("compute..exhausted")
