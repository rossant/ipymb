# -*- coding: utf-8 -*-

"""Test Markdown parser and reader."""

#------------------------------------------------------------------------------
# Imports
#------------------------------------------------------------------------------

from ...core.format_manager import format_manager, convert
from ...utils.utils import _diff, _show_outputs
from ._utils import (_test_reader, _test_writer,
                     _exec_test_file, _read_test_file)
from ..markdown import MarkdownReader, MarkdownWriter


#------------------------------------------------------------------------------
# Test Markdown parser
#------------------------------------------------------------------------------

def _test_markdown_reader(basename, ignore_notebook_meta=False):
    """Check that (test cells) and (test contents ==> cells) are the same."""
    converted, expected = _test_reader(basename, 'markdown',
                                       ignore_notebook_meta)
    assert converted == expected


def _test_markdown_writer(basename):
    """Check that (test contents) and (test cells ==> contents) are the same.
    """
    converted, expected = _test_writer(basename, 'markdown')
    assert _diff(converted, expected) == ''


def _test_markdown_markdown(basename):
    """Check that the double conversion is the identity."""

    contents = _read_test_file(basename, 'markdown')
    cells = convert(contents, from_='markdown')
    converted = convert(cells, to='markdown')

    assert _diff(contents, converted) == ''


def test_markdown_reader():
    _test_markdown_reader('ex1')
    _test_markdown_reader('ex2')
    _test_markdown_reader('ex3')
    _test_markdown_reader('ex4', ignore_notebook_meta=False)


def test_markdown_writer():
    _test_markdown_writer('ex1')
    _test_markdown_writer('ex2')
    _test_markdown_writer('ex3')
    _test_markdown_writer('ex4')


def test_markdown_markdown():
    _test_markdown_markdown('ex1')
    _test_markdown_markdown('ex2')
    _test_markdown_markdown('ex3')
    _test_markdown_markdown('ex4')


def test_decorator():
    """Test a bug fix where empty '...' lines were added to the output."""

    markdown = '\n'.join(('```',  # Not putting python still works thanks
                                  # to the input prompt.
                          '>>> @decorator',
                          '... def f():',
                          '...     """Docstring."""',
                          '...',
                          '...     # Comment.',
                          '...     pass',
                          '...',
                          '...     # Comment.',
                          '...     pass',
                          '...     pass',
                          'blah',
                          'blah',
                          '```'))

    cells = convert(markdown, from_='markdown')

    assert '...' not in cells[0]['input']
    assert cells[0]['output'] == 'blah\nblah'

    markdown_bis = convert(cells, to='markdown')
    assert _diff(markdown, markdown_bis.replace('python', '')) == ''


def test_md_notebook_metadata():
    """Test that reading and writing complex notebook metadata
    results in the identity. """
    mock_metadata = '\n'.join(('---',
                               'author: John Doe',
                               'date: 2017-05-07',
                               'output:',
                               '  html_document:',
                               '  - --title-prefix',
                               '  - Foo',
                               '  - --id-prefix',
                               '  - Bar',
                               '  toc: true',
                               '  toc_float:',
                               '    collapsed: false',
                               '    smooth_scroll: false',
                               'title: Habits',
                               '---',
                               ''))

    mdreader = MarkdownReader()
    cells = mdreader.read(mock_metadata)

    mdwriter = MarkdownWriter()
    mdwriter.write_notebook_metadata(cells[0]['metadata'])

    assert mdwriter.contents == mock_metadata
