import numpy as np
import pytest
from conversationgenome.utils.Utils import Utils


def test_safe_value_none():
    assert Utils.safe_value(None) == 0.0


def test_safe_value_nan():
    assert Utils.safe_value(np.nan) == 0.0


def test_safe_value_float():
    assert Utils.safe_value(3.14) == 3.14


def test_safe_value_int():
    assert Utils.safe_value(42) == 42


def test_safe_value_str():
    assert Utils.safe_value("test") == "test"


def test_safe_value_bool():
    assert Utils.safe_value(True) is True


def test_safe_value_numpy_array():
    arr = np.array([
        np.float64(0.6603625972570843), np.float64(0.6095246510949066),
        np.float64(0.6562667357581294), np.float64(0.6497091819269162),
        np.float64(0.592988679728645), np.float64(0.6130020980774428),
        np.float64(0.6874548512781428), np.float64(0.6664986614293865),
        np.float64(0.6033494958351422), np.float64(0.6017652504044572),
        np.float64(0.5942755016756684), np.float64(0.6552286764630223),
        np.float64(0.6426896566135323), np.float64(0.6265698059764568)
    ])
    assert np.allclose(Utils.safe_value(arr), arr)


def test_safe_value_numpy_array_with_nan():
    arr = np.array([np.nan, 1.0, 2.0])
    result = Utils.safe_value(arr)
    assert np.isnan(result[0]) and result[1] == 1.0 and result[2] == 2.0


def test_safe_value_empty_list():
    assert Utils.safe_value([]) == []


def test_safe_value_empty_numpy_array():
    arr = np.array([])
    assert np.array_equal(Utils.safe_value(arr), arr)


@pytest.mark.parametrize("v,expected", [
    (np.float64(np.nan), 0.0),
    (np.float32(np.inf), 0.0),
    (np.float64(-np.inf), 0.0),
    (float('inf'), 0.0),
    (float('-inf'), 0.0),
    (np.float32(1.2345), 1.2345),
    (np.int64(42), 42),
])
def test_safe_value_scalars_various(v, expected):
    assert Utils.safe_value(v) == expected


def test_safe_value_numpy_array_with_inf_pass_through():
    arr = np.array([1.0, np.inf, -np.inf, np.nan])
    out = Utils.safe_value(arr)

    assert np.allclose(out, arr, equal_nan=True)

def test_safe_value_empty_numpy_array():
    arr = np.array([])

    assert np.array_equal(Utils.safe_value(arr), arr)