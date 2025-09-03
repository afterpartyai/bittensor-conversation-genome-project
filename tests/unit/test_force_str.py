import pytest
from pydantic import BaseModel, ValidationError

from conversationgenome.utils.types import ForceStr


class Model(BaseModel):
    guid: ForceStr


@pytest.mark.parametrize(
    "input_value, expected",
    [
        ("abc", "abc"),
        (1616465465, "1616465465"),  # int -> str
        ("  xyz  ", "xyz"),  # strips whitespace
        (0, "0"),  # edge numeric
        ("0", "0"),
    ],
)
def test_force_str_valid_inputs(input_value, expected):
    m = Model.model_validate({"guid": input_value})
    assert isinstance(m.guid, str)
    assert m.guid == expected


@pytest.mark.parametrize(
    "input_value, expected_msg",
    [
        (None, "guid cannot be None"),
        ("", "guid cannot be empty"),
        ("   ", "guid cannot be empty"),
    ],
)
def test_force_str_invalid_inputs(input_value, expected_msg):
    with pytest.raises(ValidationError) as exc:
        Model.model_validate({"guid": input_value})
    assert expected_msg in str(exc.value)
