
from ai_agent.utils.buggy_math import divide

def test_divide_positive_numbers():
    assert divide(10, 2) == 5

def test_divide_by_zero():
    # This test is expected to fail due to the intentional bug
    try:
        divide(10, 0)
        assert False, "Expected ZeroDivisionError, but no error was raised."
    except ZeroDivisionError:
        assert True

def test_divide_negative_numbers():
    assert divide(-10, 2) == -5
    assert divide(10, -2) == -5
    assert divide(-10, -2) == 5
