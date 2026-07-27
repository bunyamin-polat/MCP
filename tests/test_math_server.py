from servers.math_server import add, multiply


def test_add():
    assert add(3, 5) == 8


def test_add_negative_numbers():
    assert add(-2, -3) == -5


def test_multiply():
    assert multiply(3, 5) == 15


def test_multiply_by_zero():
    assert multiply(7, 0) == 0
