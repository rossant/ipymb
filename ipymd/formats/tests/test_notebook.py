# -*- coding: utf-8 -*-

"""Test notebook parser and reader."""

#------------------------------------------------------------------------------
# Imports
#------------------------------------------------------------------------------

from ...core.format_manager import format_manager, convert
from ...lib.notebook import _assert_notebooks_equal
from ...utils.utils import _diff, _show_outputs
from ._utils import (_test_reader, _test_writer,
                     _exec_test_file, _read_test_file)


#------------------------------------------------------------------------------
# Test notebook parser
#------------------------------------------------------------------------------

def _test_notebook_reader(basename):
    """Check that (test cells) and (test nb ==> cells) are the same."""
    converted, expected = _test_reader(basename, 'notebook')
    assert converted == expected


def _test_notebook_writer(basename, check_outputs=True):
    """Check that (test nb) and (test cells ==> nb) are the same.
    """
    converted, expected = _test_writer(basename, 'notebook')

    _assert_notebooks_equal(converted, expected, check_notebook_metadata=False,
                            check_cell_outputs=check_outputs)


def _test_notebook_notebook(basename, check_outputs=True):
    """Check that the double conversion is the identity."""

    contents = _read_test_file(basename, 'notebook')
    cells = convert(contents, from_='notebook')
    converted = convert(cells, to='notebook')

    _assert_notebooks_equal(contents, converted, check_notebook_metadata=False,
                            check_cell_outputs=check_outputs)


def test_notebook_reader():
    _test_notebook_reader('ex1')
    _test_notebook_reader('ex2')
    _test_notebook_reader('ex3')


def test_notebook_writer():
    _test_notebook_writer('ex1')
    # Ex2 contains an image, which is not supported by ipymd internal format
    _test_notebook_writer('ex2', check_outputs=False)
    _test_notebook_writer('ex3')


def test_notebook_notebook():
    _test_notebook_notebook('ex1')
    # Ex2 contains an image, which is not supported by ipymd internal format
    _test_notebook_notebook('ex2', check_outputs=False)
    _test_notebook_notebook('ex3')
