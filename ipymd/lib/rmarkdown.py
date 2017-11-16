import re
from collections import namedtuple, OrderedDict
import base64
import json
from ipymd.ext.six import string_types
from html import escape as _html_escape

try:
    import nbformat as nbf
    from nbformat.v4.nbbase import validate
except ImportError:
    import IPython.nbformat as nbf
    from IPython.nbformat.v4.nbbase import validate

Token = namedtuple("Token", ['kind', 'value'])

# We will accept R and Python literals for boolean
# values in the markdown document
str_to_literal = {
    "NULL": None,
    "None": None,
    "False": False,
    "FALSE": False,
    "True": True,
    "TRUE": True
}

literal_to_str = {
    True: "TRUE",
    False: "FALSE",
    None: "NULL"
}


def _b64_encode(text):
    """Encode a string to base64. Unlike base64.b64encode,
    input and output are utf-8 strings. """
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')


def _tokenize_chunk_options(options_line):
    """
    Break an options line into a list of tokens.

    Chunk options-line parser.
    See *Python Cookbook* 3E, recipie 2.18

    (c) Tom Augspurger - pystitch

    Parameters
    ----------
    options_line : str

    Returns
    -------
    tokens : list of tuples

    Notes
    -----
    The valid tokens are
      * ``KWARG``: an expression line ``foo=bar``
      * ``ARG``: a term like `python`; used for kernel & chunk names
      * ``OPEN``: The literal ``{``
      * ``CLOSE``: The literal ``}``
      * ``BLANK``: Whitespace
    """
    KWARG = r'(?P<KWARG>([^,=]+ *)= *(".*"|\'.*\'|[^,=}]+))'
    ARG = r'(?P<ARG>\w+)'
    OPEN = r'(?P<OPEN>{ *)'
    DELIM = r'(?P<DELIM> *, *)'
    CLOSE = r'(?P<CLOSE>})'
    BLANK = r'(?P<BLANK>\s+)'

    master_pat = re.compile('|'.join([KWARG, ARG, OPEN, DELIM,
                                      CLOSE, BLANK]))

    def generate_tokens(pat, text):
        scanner = pat.scanner(text)
        for m in iter(scanner.match, None):
            yield Token(m.lastgroup, m.group(m.lastgroup))

    tok = list(generate_tokens(master_pat, options_line))
    return tok


def _parse_option_value(value):
    """Parse a value given as string to the appropriate data type. """
    value = value.strip()
    if value in str_to_literal:
        # special value
        return str_to_literal[value]
    elif value.startswith('"') and value.endswith('"'):
        # double quoted string
        return value.strip('"')
    elif value.startswith("'") and value.endswith("'"):
        # single quoted string
        return value.strip("'")
    else:
        try:
            # Number: int
            return int(value)
        except ValueError:
            try:
                # Number: float
                return float(value)
            except ValueError:
                # something else
                raise TypeError(
                    "Unknown data type in chunk option: {}".format(value))


def _option_value_str(value):
    """Convert an option value to the corresponding string"""
    try:
        return literal_to_str[value]
    except KeyError:
        # quote a string
        if isinstance(value, string_types):
            return '"{}"'.format(value)
        else:
            return str(value)


def _process_cell_metadata(kwargs):
    """process kwargs such as foo='bar', cat="gold", horse=9, bool_val=TRUE"""
    def process_kwarg(kwarg):
        key, value = kwarg.split("=")
        return key, _parse_option_value(value)

    return OrderedDict([process_kwarg(kwarg) for kwarg in kwargs])


def _is_code_chunk(chunk_lang):
    """determine from ```<chunk_lang>... if the chunk is executable code
     or documentation code (markdown) """
    return chunk_lang.startswith('{') and chunk_lang.endswith('}')


def _parse_chunk_meta(meta_string):
    """Process a string in the form
    {r chunk_name, foo='bar', cat="gold", horse=9, bool_val=TRUE}"""
    tokens = _tokenize_chunk_options(meta_string)
    args = []
    kwargs = []
    for kind, value in tokens:
        if kind == "ARG":
            args.append(value)
        elif kind == "KWARG":
            kwargs.append(value)

    lang = args[0]
    name = None if len(args) <= 1 else args[1]
    meta = _process_cell_metadata(kwargs)

    return lang, name, meta


def _read_rmd_b64(b64):
    decoded = base64.b64decode(b64).decode('utf-8')
    return json.loads(decoded, encoding='utf-8')


def _get_nb_html_path(rmd_path):
    assert rmd_path.endswith(".Rmd"), "invalid file extension"
    return re.sub(r"\.Rmd$", ".nb.html", rmd_path)


def _merge_consecutive_markdown_cells(cells):
    """Merge consecutive cells with cell_type == 'markdown'.

    Parameters
    ----------
    cells : a list of jupyter notebook cells.
    """
    merged = []
    tmp_cell = None

    def done_merging():
        """execute, when switching back from a series of markdown
        cells to other cell types"""
        nonlocal merged, tmp_cell
        if tmp_cell is not None:
            merged.append(tmp_cell)
            tmp_cell = None

    for cell in cells:
        if cell['cell_type'] == 'markdown':
            if tmp_cell is None:
                tmp_cell = cell
            else:
                if 'source' in cell:
                    tmp_cell['source'] = tmp_cell.get('source', "") + "\n\n" + cell['source']
                if 'metadata' in cell:
                    tmp_cell['metadata'] = tmp_cell.get('metadata', {}).update(cell['metadata'])
        else:
            done_merging()
            merged.append(cell)

    done_merging()

    return merged


def html_escape(s):
    """escape HTML and double quotes only. """
    return _html_escape(s, quote=False).replace('"', "&quot;")


class HtmlNbChunkCell(object):
    NO_CODE_FROM_HTMLNB = "Code is not parsed from .html.nb. " \
                          "Use code provided by *.Rmd instead. "
    NO_META_FROM_HTMLNB = "Cell metadata is not parsed from .html.nb. " \
                          "Use metadata provided by *.Rmd instead. "

    def __init__(self, execution_count):
        self._count = execution_count
        self._cell = nbf.v4.new_code_cell(self.NO_CODE_FROM_HTMLNB,
                                          execution_count=self._count)

    def new_output(self, tag, b64):
        meta = _read_rmd_b64(b64)
        mime = meta.get('mime', 'text/plain')
        self._cell.outputs.append(

            nbf.v4.new_output('execute_result',
                              {mime: meta['data'].strip()},
                              execution_count=self._count,
                              # metadata={"output_type": tag}))
                              metadata={}))

    def new_plot(self, mime, data, b64):
        meta = {} if not b64 else _read_rmd_b64(b64)
        self._cell.outputs.append(
            nbf.v4.new_output('execute_result',
                              {mime: data},
                              execution_count=self._count,
                              metadata=meta)
        )

    def new_error(self, b64):
        err_dict = {} if not b64 else _read_rmd_b64(b64)
        traceback = [str(x) for x in err_dict.get("traceback", [])]
        ename = err_dict.get("ename", "")
        evalue = err_dict.get("evalue", "")
        self._cell.outputs.append(
            nbf.v4.new_output('error',
                              traceback=traceback,
                              ename=ename,
                              evalue=evalue)
        )

    @property
    def cell(self):
        return self._cell
