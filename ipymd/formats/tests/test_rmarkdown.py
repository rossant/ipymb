# -*- coding: utf-8 -*-

"""Test Markdown parser and reader."""

# ------------------------------------------------------------------------------
# Imports
# ------------------------------------------------------------------------------

from ipymd.core.format_manager import convert, format_manager
from ._utils import _read_test_file
from ...utils.utils import _full_diff
from ...lib.notebook import _assert_notebooks_equal
from ipymd.formats.rmarkdown import HtmlNbChunkCell, RmarkdownWriter, \
    RmarkdownReader, RmdWriter, RmdReader, NbHtmlWriter, HtmlNbReader, \
    RMD_FORMAT

from collections import OrderedDict
import json


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
    assert result == [('text', 'text contents'),
                      ('chunk', '<!-- chunk contents -->')]


def test_htmlnb_parse_image():
    htmlnbreader = HtmlNbReader()

    html = '<p><img src="data:image/png;base64,iVBORw0KGgoAAAANSUhE' \
           'UgAAAjwAAAFhCAMAAABDKYAcAAACTFBMVEUAAAA\nBAQEJCQ...==" /></p>'
    mime, data = list(htmlnbreader._parse_image(html))
    assert mime == 'image/png'
    assert data == "iVBORw0KGgoAAAANSUhEUgAAAjwAAAFhCAMAAABDKYAcAAACT" \
                   "FBMVEUAAAA\nBAQEJCQ...=="

    html = ('<!-- rnb-plot-begin -->\n'
            '<p><img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAWQA'
            'AAD8CAYAAABAWd66AAAABHNCSVQICAgIfAhkiAAAAAlwSFlz\n'
            'AAALEgAACxIB0t1+/AAACDBJREFUeJzt3c2LnWcZx/Hf1RmlScW'
            'XklJwWpzKiCUIUglSLbiwLnxD\n" /></p>\n'
            '<!-- rnb-plot-end -->')
    mime, data = list(htmlnbreader._parse_image(html))
    assert mime == 'image/png'
    assert data == "iVBORw0KGgoAAAANSUhEUgAAAWQAAAD8CAYAAABAWd66AAAABHNCSV" \
                   "QICAgIfAhkiAAAAAlwSFlz\n" \
                   "AAALEgAACxIB0t1+/AAACDBJREFUeJzt3c2LnWcZx/Hf1RmlScW" \
                   "XklJwWpzKiCUIUglSLbiwLnxD\n"

    html = """<p><a>some other html</a></p>"""
    mime, data = list(htmlnbreader._parse_image(html))
    assert mime == 'text/plain'
    assert data == 'IPYMD: Error reading image.'


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
            "data": {'image/png': "iVBORw0KGgoAAAANSUhEUgAAAjwAAAFhCAMAAABD"
                                  "KYAcAAACTFBMVEUAAAABAQEJCQ...=="}
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
            "metadata": {},
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
        'metadata': {},
        'data': {"text/plain": "[1]  1  2  3  4  5  6  7  8  9 10"},
        "execution_count": 1
    }]


def test_rmarkdown_merge_cells_inconsistent_input():
    """test that source and output are not merged when the sources
    are inconsistent. """
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
    assert (nb['cells'][0]['source'] == nb['cells'][1]['source']
            == 'print(1:10)')
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

    rmdreader = RmdWriter(RmarkdownWriter())
    result = rmdreader._encode_metadata(chunk_meta)
    # we know that all strings will be double-quoted.
    expected = expected.replace("'", '"')
    assert expected == result


# ------------------------------------------------------------------------------
# Test Format
# ------------------------------------------------------------------------------

"""
Testing reading and writing of Rmd notebooks. 

We have the issue that we cannot *exactly* reproduce the HTML 
generated by rstudio (and there is no point in trying hard 
to do so, as this might also change over time). 

Therefore, an assertion for *writing* exactly the same .nb.html is futile. 
We circumvent this problem by splitting up the test files in 
*.rstudio.{rmd,nb.html} and *.{rmd,nb.html}.

While the reader should be able to correctly read both of the file formats 
(i.e. nb.html as generated by rstudio and ipymd), the writer only has
to be consistent with the ipymd version. 

## The round-trip-conversion test
By checking that rmarkdown can be correctly converted to rmarkdown
we ensure that no information is lost.

By checking that a notebook can be correctly converted to a notebook
and back, we ensure that a notebook can be represented 
in rmarkdown without any information loss, i.e. rmarkdown is a
full replacement for .ipynb.

## Compatibility with rstudio
While we can ensure automatically, that reading rmarkdown generated
with rstudio works, we cannot test (easily) that rstudio correctly 
reads rmarkdown generated by ipymd. This would require to implement
tests in R instead of python. 
"""

# register rstudio rmarkdown dialect to the format manager.
_fm = format_manager()
_fm.register(name='rmarkdown.rstudio', **RMD_FORMAT)
# ipymd only makes sense with verbose metadata
_fm.verbose_metadata = True


def _test_rmarkdown_reader(basename):
    """Check that reading Rmarkdown (.Rmd + .nb.html) results
    in the correct notebook (.ipynb).
    """
    contents = _read_test_file(basename, 'rmarkdown')
    contents_rstudio = _read_test_file(basename, 'rmarkdown.rstudio')
    expected = _read_test_file(basename, 'notebook')
    converted = convert(contents, from_='rmarkdown', to='notebook')
    converted_rstudio = convert(contents_rstudio, from_='rmarkdown',
                                to='notebook')

    # for ipymd rmd notebook, metadata must be equal
    _assert_notebooks_equal(expected, converted, check_cell_metadata=True,
                            check_notebook_metadata=True)

    # we must be able to correctly read an Rmd created by rstudio,
    # but we cannot expect all metadata to be there
    _assert_notebooks_equal(expected, converted_rstudio,
                            check_cell_metadata=False,
                            check_notebook_metadata=False)


def _test_rmarkdown_writer(basename):
    """Check that writing a notebook (.ipynb) to Rmarkdown results
    in the correct .Rmd + .nb.html files"""
    contents = _read_test_file(basename, 'notebook')
    expected = _read_test_file(basename, 'rmarkdown')
    expected_rstudio = _read_test_file(basename, 'rmarkdown.rstudio')
    converted = convert(contents, to='rmarkdown', from_='notebook')

    # The writer must produce exactly the rmd/html we want
    assert converted['rmd'] == expected['rmd']
    assert converted['html'] == expected['html']

    # However, we cannot expect to generate exactly the same result
    # as rstudio (minor things like markdown->HTML conversion.
    # We want to have a diff for development purposes, though
    print("Diff converted Rmd with {}.rmarkdown.rstudio.Rmd\n".format(
        basename))
    print(_full_diff(converted['rmd'], expected_rstudio['rmd']))
    print('\n\n')

    print("Diff converted nb.html with {}.rmarkdown.rstudio.nb.html\n".format(
        basename))
    print(_full_diff(converted['html'], expected_rstudio['html']))
    print('\n\n')


def _test_rmarkdown_rmarkdown(basename):
    """Check that the double conversion is the identity."""
    contents = _read_test_file(basename, 'rmarkdown')
    notebook = convert(contents, from_='rmarkdown', to='notebook')
    notebook_dict = json.loads(json.dumps(notebook))
    converted = convert(notebook_dict, from_='notebook', to='rmarkdown')

    assert converted['rmd'] == contents['rmd']
    assert converted['html'] == contents['html']


def _test_notebook_notebook(basename):
    """check that converting a notebook to Rmarkdown and back
    is the identity"""
    contents = _read_test_file(basename, 'notebook')
    rmarkdown = convert(contents, from_='notebook', to='rmarkdown')
    converted = convert(rmarkdown, from_='rmarkdown', to='notebook')

    # TODO cell metadata? unimportant metadata(collapsed...)
    _assert_notebooks_equal(contents, converted, check_cell_metadata=True)


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


def test_ex6_notebook_notebook():
    _test_notebook_notebook('ex6')
