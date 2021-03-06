import os

import pytest

from paramtools import Parameters

CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))


@pytest.fixture
def field_map():
    # nothing here for now
    return {}


@pytest.fixture
def schema_def_path():
    return os.path.join(CURRENT_PATH, "../../examples/behresp/schema.json")


@pytest.fixture
def defaults_spec_path():
    return os.path.join(CURRENT_PATH, "../../examples/behresp/defaults.json")


@pytest.fixture
def BehrespParams(schema_def_path, defaults_spec_path):
    class _BehrespParams(Parameters):
        schema = schema_def_path
        defaults = defaults_spec_path

    return _BehrespParams


def test_load_schema(BehrespParams):
    params = BehrespParams()
    assert params
