# -*- coding: utf-8 -*-

"""Test Markdown parser and reader."""

# ------------------------------------------------------------------------------
# Imports
# ------------------------------------------------------------------------------

from ipymd.core.format_manager import format_manager, convert
from ipymd.utils.utils import _diff, _show_outputs, _read_text, _ensure_string
from ._utils import (_test_reader, _test_writer,
                     _exec_test_file, _read_test_file, _test_file_path)
from ._notebook_utils import _assert_notebooks_equal
from ipymd.formats.rmarkdown import *

from collections import OrderedDict


# ------------------------------------------------------------------------------
# Test Rmarkdown classes and helper functions
# ------------------------------------------------------------------------------

def test_htmlnb_parse_html():
    html = """
    <!-- rnb-text-begin -->
    text contents
    <!-- rnb-text-end -->
    <!-- rnb-chunk-begin -->
    <!-- chunk contents --> 
    <!-- rnb-chunk-end -->
    """
    htmlnbreader = HtmlNbReader()
    result = list(htmlnbreader._parse_html(html))
    assert result == [('text', 'text contents'), ('chunk', '<!-- chunk contents -->')]


def test_htmlnb_parse_image():
    htmlnbreader = HtmlNbReader()

    html = """
    <p><img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAjwAAAFhCAMAAABDKYAcAAACTFBMVEUAAAABAQEJCQ...==" /></p>
    """
    mime, data = list(htmlnbreader._parse_image(html))
    assert mime == 'image/png'
    assert data == "iVBORw0KGgoAAAANSUhEUgAAAjwAAAFhCAMAAABDKYAcAAACTFBMVEUAAAABAQEJCQ...=="

    html = """<p><a>some other html</a></p>"""
    mime, data = list(htmlnbreader._parse_image(html))
    assert mime == 'text/plain'
    assert data == 'Error reading image.'


def test_htmlnb_chunk_cell():
    html = """
    <!-- rnb-chunk-begin -->
    <!-- rnb-source-begin eyJkYXRhIjoiYGBgclxuZ2dwbG90KGRhdGEuZnJhbWUoeD0xOjEwKSwgYWVzKHk9eCwgeD14KSkgKyBnZW9tX3BvaW50KClcbmBgYCJ9 -->
    <pre class="r"><code>ggplot(data.frame(x=1:10), aes(y=x, x=x)) + geom_point()</code></pre>
    <!-- rnb-source-end -->
    <!-- rnb-plot-begin e30= -->
    <p><img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAjwAAAFhCAMAAABDKYAcAAACTFBMVEUAAAABAQEJCQ...==" /></p>
    <!-- rnb-plot-end -->
    <!-- rnb-chunk-end -->"""

    htmlnbreader = HtmlNbReader()
    assert htmlnbreader._chunk_cell(html) == {
      "cell_type": "code",
      "execution_count": 1,
      "source": HtmlNbChunkCell.NO_CODE_FROM_HTMLNB,
      "metadata": {},
      "outputs": [{
          # list of output dicts (described below)
          "execution_count": 1,
          "output_type": "execute_result",
          "metadata": {},
          "data": {'image/png': "iVBORw0KGgoAAAANSUhEUgAAAjwAAAFhCAMAAABDKYAcAAACTFBMVEUAAAABAQEJCQ...=="}
      }]
    }


def test_htmlnb_chunk_cell2():
    html = """
    <!-- rnb-source-begin eyJkYXRhIjoiYGBgclxucHJpbnQoMToxMClcbmBgYCJ9 -->
    <pre class="r"><code>print(1:10)</code></pre>
    <!-- rnb-source-end -->
    <!-- rnb-output-begin eyJkYXRhIjoiIFsxXSAgMSAgMiAgMyAgNCAgNSAgNiAgNyAgOCAgOSAxMFxuIn0= -->
    <pre><code> [1]  1  2  3  4  5  6  7  8  9 10</code></pre>
    <!-- rnb-output-end -->
    """

    htmlnbreader = HtmlNbReader()
    assert htmlnbreader._chunk_cell(html) == {
        "cell_type": "code",
        "execution_count": 1,
        "source": HtmlNbChunkCell.NO_CODE_FROM_HTMLNB,
        "metadata": {},
        "outputs": [{
            # list of output dicts (described below)
            "execution_count": 1,
            "output_type": "execute_result",
            "metadata": {'output_type': 'output'},
            "data": {'text/plain': "[1]  1  2  3  4  5  6  7  8  9 10"}
        }]
    }


def test_rmd_read_cell_metadata():
    """test that metadata from chunk options is correctly read. """
    chunk1 = \
        """```{r test, str_type="foo", str_single_quote='bar', int_type=42, bool_type=TRUE, null_type=NULL}\n\n```"""
    chunk2 = \
        """```{python, str_type="foo", str_single_quote='bar', int_type=42, bool_type=TRUE, null_type=NULL}\n\n```"""
    chunk_meta = OrderedDict([('str_type', 'foo'),
                              ('str_single_quote', 'bar'),
                              ('int_type', 42),
                              ('bool_type', True),
                              ('null_type', None)])

    rmdreader = RmdReader()
    cell1 = rmdreader.read(chunk1)[0]
    cell2 = rmdreader.read(chunk2)[0]
    assert cell1['lang'] == 'r'
    assert cell2['lang'] == 'python'
    assert cell1['metadata'] == chunk_meta
    assert cell2['metadata'] == chunk_meta


def test_rmd_read_notebook_metadata():
    """test that notebook metadata is properly read."""
    rmd = """---\ntitle: "R Notebook"\noutput: html_notebook\n---"""

    rmdreader = RmdReader()
    nb_metadata = rmdreader.read(rmd)[0]
    assert nb_metadata['metadata'] == {
        "title": "R Notebook",
        "output": "html_notebook"
    }


def test_rmarkdown_read_notebook_metadata():
    """test that notebook metadata is properly read."""
    contents = {
        "rmd": """---\ntitle: "R Notebook"\noutput: html_notebook\n---""",
        "html": None
    }

    reader = RmarkdownReader()
    nb = reader.read(contents)
    assert nb['metadata'] == {
        "title": "R Notebook",
        "output": "html_notebook"
    }


def test_rmarkdown_merge_cells():
    """test that source and output are correctly merged. """
    contents = {
        "rmd": """```{r}\nprint(1:10)\n```""",
        "html": """
            <!-- rnb-chunk-begin -->
            <!-- rnb-source-begin eyJkYXRhIjoiYGBgclxucHJpbnQoMToxMClcbmBgYCJ9 -->
            <pre class="r"><code>print(1:10)</code></pre>
            <!-- rnb-source-end -->
            <!-- rnb-output-begin eyJkYXRhIjoiIFsxXSAgMSAgMiAgMyAgNCAgNSAgNiAgNyAgOCAgOSAxMFxuIn0= -->
            <pre><code> [1]  1  2  3  4  5  6  7  8  9 10</code></pre>
            <!-- rnb-output-end -->
            <!-- rnb-chunk-end -->
            """
    }

    reader = RmarkdownReader()
    nb = reader.read(contents)
    cell = nb['cells'][0]
    assert cell['source'] == 'print(1:10)'
    assert cell['outputs'] == [{
        "output_type": "execute_result",
        'metadata': {'output_type': 'output'},
        'data': {"text/plain": "[1]  1  2  3  4  5  6  7  8  9 10"},
        "execution_count": 1
    }]


def test_rmarkdown_merge_cells_inconsistent_input():
    """test that source and output are not merged when the sources are inconsistent. """
    contents = {
        "rmd": """```{r}\nprint(1:10)\n```\n\n```{r}\nprint(1:10)\n```""",
        "html": """
            <!-- rnb-chunk-begin -->
            <!-- rnb-source-begin eyJkYXRhIjoiYGBgclxucHJpbnQoMToxMClcbmBgYCJ9 -->
            <pre class="r"><code>print(1:10)</code></pre>
            <!-- rnb-source-end -->
            <!-- rnb-output-begin eyJkYXRhIjoiIFsxXSAgMSAgMiAgMyAgNCAgNSAgNiAgNyAgOCAgOSAxMFxuIn0= -->
            <pre><code> [1]  1  2  3  4  5  6  7  8  9 10</code></pre>
            <!-- rnb-output-end -->
            <!-- rnb-chunk-end -->
            """
    }

    reader = RmarkdownReader()
    nb = reader.read(contents)
    assert nb['cells'][0]['source'] == nb['cells'][1]['source'] == 'print(1:10)'
    assert nb['cells'][0]['outputs'] == nb['cells'][0]['outputs'] == []


def test_rmd_write_cell_metadata():
    """test that cell metadata is properly encoded."""
    expected = """r test, str_type="foo", str_single_quote='bar', int_type=42, bool_type=TRUE, null_type=NULL"""
    chunk_meta = OrderedDict([('lang', 'r'),
                              ('name', 'test'),
                              ('str_type', 'foo'),
                              ('str_single_quote', 'bar'),
                              ('int_type', 42),
                              ('bool_type', True),
                              ('null_type', None)])

    rmdreader = RmdWriter()
    result = rmdreader._encode_metadata(chunk_meta)
    expected = expected.replace("'", '"')  # we know that all strings will be double-quoted.
    assert expected == result

# ------------------------------------------------------------------------------
# Test Format
# ------------------------------------------------------------------------------

def _test_rmarkdown_reader(basename):
    """Check that reading Rmarkdown (.Rmd + .nb.html) results in the correct notebook (.ipynb). """
    contents = _read_test_file(basename, 'rmarkdown')
    expected = _read_test_file(basename, 'notebook')
    converted = convert(contents, from_='rmarkdown')
    # TODO check metadata
    _assert_notebooks_equal(expected, converted, check_cell_metadata=False, check_notebook_metadata=False)


def _test_rmarkdown_writer(basename):
    """Check that writing a notebook (.ipynb) to Rmarkdown results in the correct .Rmd + .nb.html files"""
    contents = _read_test_file(basename, 'notebook')
    expected = _read_test_file(basename, 'rmarkdown')
    converted = convert(contents, to_='rmarkdown')
    assert converted['rmd'] == expected['rmd']
    assert converted['html'] == expected['html']


def _test_rmarkdown_rmarkdown(basename):
    """Check that the double conversion is the identity."""

    contents = _read_test_file(basename, 'rmarkdown')
    notebook = convert(contents, from_='rmarkdown')
    converted = convert(notebook, to='rmarkdown')

    assert converted['rmd'] == contents['rmd']
    assert converted['html'] == contents['html']


def test_ex5_reader():
    _test_rmarkdown_reader('ex5')


def test_ex5_writer():
    _test_rmarkdown_writer('ex5')


def test_ex5_rmarkdown_rmarkdown():
    _test_rmarkdown_rmarkdown('ex5')


def test_ex6_reader():
    _test_rmarkdown_reader('ex6')


def test_ex6_writer():
    _test_rmarkdown_writer('ex6')


def test_ex6_rmarkdown_rmarkdown():
    _test_rmarkdown_rmarkdown('ex6')




