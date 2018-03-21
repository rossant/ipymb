"""Test rmarkdown helper functions. """


from ipymd.lib.rmarkdown import _merge_consecutive_markdown_cells, \
    _read_rmd_b64, _option_value_str, \
    _parse_option_value, _parse_chunk_meta
from collections import OrderedDict


def test_merge_consecutive_markdown_cells():
    """Test that consecutive markdown cells are correctly merged. """
    cells = [
        {'cell_type': 'notebook_metadata'},
        {'cell_type': 'markdown', 'source': '1'},
        {'cell_type': 'markdown', 'source': '2', 'x': 'a'},
        {'cell_type': 'markdown'},
        {'cell_type': 'code', 'source': '1'},
        {'cell_type': 'markdown', 'source': '1'},
        {'cell_type': 'markdown'},
    ]

    assert _merge_consecutive_markdown_cells(cells) == [
        {'cell_type': 'notebook_metadata'},
        {'cell_type': 'markdown', 'source': '1\n\n2'},
        {'cell_type': 'code', 'source': '1'},
        {'cell_type': 'markdown', 'source': '1'}
    ]


def test_merge_consecutive_markdown_cells_2():
    """Test, that consecutive code cells are not merged. """
    cells = [
        {'cell_type': 'notebook_metadata'},
        {'cell_type': 'code', 'source': '1'},
        {'cell_type': 'code', 'source': '2', 'x': 'a'},
        {'cell_type': 'code'},
        {'cell_type': 'code', 'source': '1'},
        {'cell_type': 'markdown', 'source': '1'},
        {'cell_type': 'markdown'},
    ]

    assert _merge_consecutive_markdown_cells(cells) == [
        {'cell_type': 'notebook_metadata'},
        {'cell_type': 'code', 'source': '1'},
        {'cell_type': 'code', 'source': '2', 'x': 'a'},
        {'cell_type': 'code'},
        {'cell_type': 'code', 'source': '1'},
        {'cell_type': 'markdown', 'source': '1'}
    ]


def test_read_rmd_base64():
    expected = {"data": "```python\nfoo = 'bar'\n```"}
    b64 = "eyJkYXRhIjoiYGBgcHl0aG9uXG5mb28gPSAnYmFyJ1xuYGBgIn0="
    assert _read_rmd_b64(b64) == expected


def test_parse_chunk_meta():
    chunk_meta = \
        """{r chunk_name, foo='bar', cat="gold", horse=9, bool_val=TRUE}"""
    lang, name, meta = _parse_chunk_meta(chunk_meta)
    assert lang == 'r'
    assert name == 'chunk_name'
    assert meta == OrderedDict([
        ('foo', 'bar'), ('cat', 'gold'), ('horse', 9), ('bool_val', True)
    ])


def test_option_value_str():
    assert _option_value_str(True) == "TRUE"
    assert _option_value_str("foo") == '"foo"'
    assert _option_value_str(42) == "42"
    assert _option_value_str(None) == "NULL"


def test_parse_option_value():
    assert _parse_option_value("'True'") == "True"
    assert _parse_option_value('"TRUE"') == "TRUE"
    assert _parse_option_value("True")
    assert _parse_option_value("TRUE")
    assert type(_parse_option_value("42")) == int
    assert type(_parse_option_value("42.")) == float
    assert type(_parse_option_value("42")) == int
