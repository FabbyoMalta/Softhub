from app.utils.cache import stable_json_hash


def test_stable_json_hash_is_order_independent():
    a = {'b': 2, 'a': {'x': [2, 1], 'y': 'z'}}
    b = {'a': {'y': 'z', 'x': [2, 1]}, 'b': 2}
    assert stable_json_hash(a) == stable_json_hash(b)
