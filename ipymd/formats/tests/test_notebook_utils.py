"""Test the notebook utils. """
from ._notebook_utils import _assert_cell_outputs_equal, _assert_notebooks_equal
from ._utils import _read_test_file
import pytest


def test_cell_outputs_equal():
    out1 = {
        "execution_count": 1,
        "output_type": "execute_result",
        "metadata": {'output_type': 'output'},
        "data": {'text/plain': "[1]  1  2  3  4  5  6  7  8  9 10"}
    }
    # execution_count modified
    out2 = {
        "execution_count": 2,
        "output_type": "execute_result",
        "metadata": {'output_type': 'output'},
        "data": {'text/plain': "[1]  1  2  3  4  5  6  7  8  9 10"}
    }
    # execution_count None
    out3 = {
        "execution_count": None,
        "output_type": "execute_result",
        "metadata": {'output_type': 'output'},
        "data": {'text/plain': "[1]  1  2  3  4  5  6  7  8  9 10"}
    }
    # stream
    out4 = {
        "output_type": "stream",
        "name": 'stdout',
        "text": "[1]  1  2  3  4  5  6  7  8  9 10"
    }
    # differing metadata
    out5 = {
        "execution_count": 1,
        "output_type": "execute_result",
        "metadata": {'foo': 'bar'},
        "data": {'text/plain': "[1]  1  2  3  4  5  6  7  8  9 10"}
    }
    _assert_cell_outputs_equal(out1, out1)
    with pytest.raises(AssertionError):
        _assert_cell_outputs_equal(out1, out2)
    _assert_cell_outputs_equal(out1, out3)
    _assert_cell_outputs_equal(out1, out4, check_metadata=False)
    _assert_cell_outputs_equal(out1, out5, check_metadata=False)
    with pytest.raises(AssertionError):
        _assert_cell_outputs_equal(out1, out5)


def test_assert_notebook_equals():
    ex1 = _read_test_file('ex1', 'notebook')
    ex4 = _read_test_file('ex4', 'notebook')
    _assert_notebooks_equal(ex1, ex1)
    _assert_notebooks_equal(ex4, ex4)
    with pytest.raises(AssertionError):
        _assert_notebooks_equal(ex1, ex4)
    with pytest.raises(AssertionError):
        _assert_notebooks_equal(ex4, ex1)
