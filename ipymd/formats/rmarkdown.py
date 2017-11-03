# -*- coding: utf-8 -*-


"""Rmarkdown readers and writers.

"""

#------------------------------------------------------------------------------
# Imports
#------------------------------------------------------------------------------

import re
import os.path

import yaml
import base64

try:
    import nbformat as nbf
    from nbformat.v4.nbbase import validate
except ImportError:
    import IPython.nbformat as nbf
    from IPython.nbformat.v4.nbbase import validate

from jinja2 import Environment, PackageLoader, select_autoescape

from ..utils.utils import _read_text, _write_text, _get_cell_types
from ..core.prompt import create_prompt
from ..lib.rmarkdown import _option_value_str, _parse_chunk_meta, _read_rmd_b64, \
    _merge_consecutive_markdown_cells, _is_code_chunk, HtmlNbChunkCell, _get_nb_html_path
from .markdown import BaseMarkdownReader, BaseMarkdownWriter

from ..core.meta import NotebookConsumer, NotebookProducer
from .notebook import IpymdToNotebookWriter

#------------------------------------------------------------------------------
# R Markdown
#------------------------------------------------------------------------------


class RmarkdownReader(NotebookProducer):
    """ read R notebook format (combine .Rmd and .nb.html) """
    def __init__(self):
        self._rmd_reader = RmdReader()
        self._html_nb_reader = HtmlNbReader()

    def read(self, contents):
        cells_rmd = list(self._rmd_reader.read(contents['rmd']))
        nb_writer = IpymdToNotebookWriter()
        for cell in cells_rmd:
            nb_writer.write(cell)
        nb_rmd = nb_writer.contents
        nb_html = self._html_nb_reader.read(contents['html'])

        nb_rmd['cells'] = _merge_consecutive_markdown_cells(nb_rmd['cells'])
        nb_html['cells'] = _merge_consecutive_markdown_cells(nb_html['cells'])

        return self._merge_notebooks(nb_rmd, nb_html)

    def _merge_notebooks(self, nb_rmd, nb_html):
        # if not consistent, discard output (do not consider html cells)
        if self._check_notebook_consistency(nb_rmd['cells'], nb_html['cells']):
            for rmd_cell, html_cell in zip(nb_rmd['cells'], nb_html['cells']):
                if 'outputs' in html_cell:
                    rmd_cell['outputs'] = html_cell['outputs']
        return nb_rmd

    def _check_notebook_consistency(self, rmd_cells, html_cells):
        """The lists of cells are considered consistent if the cell types appear in the same order. """
        return _get_cell_types(rmd_cells) == _get_cell_types(html_cells)


class RmdReader(BaseMarkdownReader):
    """Read RMarkdown .Rmd files"""
    def __init__(self, prompt=None):
        super(RmdReader, self).__init__()

    def read(self, text, rules=None):
        raw_cells = super(RmdReader, self).read(text, rules)
        cells = []

        last_index = len(raw_cells) - 1

        for i, cell in enumerate(raw_cells):
            if cell['cell_type'] == 'cell_metadata':
                if i + 1 <= last_index:
                    raw_cells[i + 1].update(metadata=cell['metadata'])
            else:
                cells.append(cell)

        return _merge_consecutive_markdown_cells(cells)

    # Parser methods
    # -------------------------------------------------------------------------

    def parse_fences(self, m):
        lang_meta = m.group(2)
        code = m.group(3).rstrip()

        if _is_code_chunk(lang_meta):
            cell = self._code_cell(code)
            lang, name, meta = _parse_chunk_meta(lang_meta)
            cell['lang'] = lang
            if name is not None:
                cell['name'] = name
            if len(meta):
                cell['metadata'] = meta
            return cell
        else:
            return self._markdown_cell_from_regex(m)

    def parse_block_code(self, m):
        return self._markdown_cell_from_regex(m)

    def parse_block_html(self, m):
        return self._markdown_cell_from_regex(m)

    def parse_text(self, m):
        return self._markdown_cell_from_regex(m)

    def parse_meta(self, m):
        return self._meta_from_regex(m)


class HtmlNbReader(object):
    """
    Read R noteboook .html.nb files.

    See Also:
        - https://github.com/rstudio/rmarkdown/blob/95b8b1fa64f78ca99f225a67fff9817103be568b/R/html_notebook.R
        - http://rmarkdown.rstudio.com/r_notebook_format.html

    """
    def_text_or_chunk = re.compile(
        r'<!-- rnb-(text|chunk)-begin -->'
        r'([\s\S]+?)'
        r'<!-- rnb-(text|chunk)-end -->'
    )

    def_chunk_element = re.compile(
        r'<!-- rnb-(source|plot|output|warning|error|message)-begin (.*?)-->'
        r'([\s\S]+?)'
        r'<!-- rnb-(source|plot|output|warning|error|message)-end -->'
    )

    def_image_element = re.compile(
        r'<img src="data:(.*?);base64,(.*?)" />'
    )

    def __init__(self):
        self._nb = nbf.v4.new_notebook()
        self._count = 1

    def read(self, html):
        if html is not None:
            for block_type, block_content in self._parse_html(html):
                if block_type == 'text':
                    self._nb['cells'].append(self._text_cell(block_content))
                else:
                    self._nb['cells'].append(self._chunk_cell(block_content))

        return self._nb

    def _parse_html(self, html):
        """ get a list of rnb-text and rnb-chunks"""
        for start_tag, contents, end_tag in self.def_text_or_chunk.findall(html):
            assert start_tag == end_tag, "text and chunk blocks must not be nested."
            yield start_tag, contents.strip()

    def _parse_image(self, html):
        try:
            mime, data = next(iter(self.def_image_element.findall(html)))
        except StopIteration:
            mime = 'text/plain'
            data = 'Error reading image.'
        return mime, data

    def _text_cell(self, text_block):
        # new markdown cell will be filled with html. The corresponding
        # source is found in .Rmd file.
        return nbf.v4.new_markdown_cell(text_block)

    def _chunk_cell(self, chunk_block):
        """parse an rnb-chunk consisting of source/plot/..."""
        # A chunk block can be divided in multiple sub-blocks, namely
        #
        # "source",  "plot", "output",
        # "warning", "error", "message"
        cell = None

        for start_tag, b64, contents, end_tag in self.def_chunk_element.findall(chunk_block):
            assert start_tag == end_tag, "different chunk elements must not be nested. "
            b64 = b64.strip()
            contents = contents.strip()
            if start_tag == 'source':
                cell = HtmlNbChunkCell(b64, self._count)
            elif start_tag in ['output', 'warning', 'error', 'message']:
                assert cell is not None, "output without source"
                cell.new_output(start_tag, b64)
            elif start_tag == 'plot':
                assert cell is not None, "plot without source"
                mime, data = self._parse_image(contents)
                cell.new_plot(mime, data, b64)

        self._count += 1
        return cell.cell


class RmarkdownWriter(NotebookConsumer):
    """Write R notebook (combine .Rmd and .nb.html) """

    def __init__(self):
        self._rmd_writer = RmdWriter()
        self._nb_html_writer = NbHtmlWriter(self._rmd_writer)

    def write_contents(self, nb):
        """convert a jupyter notebook dict to rmarkdown"""
        assert nb['nbformat'] >= 4

        self.write_notebook_metadata(nb['metadata'])
        for cell in nb['cells']:
            self.write(cell)

    def write(self, cell):
        self._rmd_writer.write(cell)
        self._nb_html_writer.write(cell)

    def write_notebook_metadata(self, metadata):
        self._rmd_writer.write_notebook_metadata(metadata)

    def close(self):
        self._rmd_writer.close()

    @property
    def contents(self):
        return {
            'rmd': self._rmd_writer.contents,
            'html': self._nb_html_writer.contents
        }

    def __del__(self):
        self.close()


class NbHtmlWriter(object):
    """ Write R notebook .nb.html """
    def __init__(self, rmd_writer):
        """

        Parameters
        ----------
        rmd_writer: RmdWriter
            a reference to the corresponding RmdWriter, as the rmd output
            will also be encoded in the html output.
        """
        self._rmd_writer = rmd_writer

    @property
    def template(self):
        """ Load the jinja2 template from the package resources. """
        env = Environment(
            loader=PackageLoader('ipymd', 'ressources'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        return env.get_template('r_notebook.template.html')

    def write(self, cell):
        pass

    @property
    def contents(self):
        base64_rmd = base64.b64encode(self._rmd_writer.contents.encode())
        return self.template.render(base64_rmd=base64_rmd)


class RmdWriter(BaseMarkdownWriter):
    """Default .Rmd writer."""

    def __init__(self):
        super(RmdWriter, self).__init__()

    def append_code(self, input, output=None, metadata=None):
        code_block = '```{{{meta}}}\n{code}\n```'.format(meta=self._encode_metadata(metadata), code=input.rstrip())
        self._output.write(code_block)

    def _encode_metadata(self, metadata):
        def encode_option(key, value):
            return "{}={}".format(key, _option_value_str(value))

        if metadata is not None:
            lang = metadata.pop('lang', 'python')  # TODO derive default lang from kernel
            name = metadata.pop('name', None)
            options = ", ".join(encode_option(k, v) for k, v in metadata.items())

        else:
            # TODO tmp workaround
            lang = "python"
            name = None
            options = ""

        out = [lang]
        if name is not None:
            out.append(" " + name)
        if len(options):
            out.append(", " + options)

        return "".join(out)

    @property
    def contents(self):
        return self._output.getvalue().rstrip() + '\n'  # end of file \n


def load_rmarkdown(path):
    """
    Read .Rmd and the corresponding .html.nb
    If .html.nb is not available, outputs will be empty.
    """
    html_path = _get_nb_html_path(path)
    return {
        'rmd': _read_text(path),
        'html': _read_text(html_path) if os.path.isfile(html_path) else None
    }


def save_rmarkdown(path, contents):
    """
    store cells to .Rmd and outputs to .html.nb
    """
    html_path = _get_nb_html_path(path)
    _write_text(path, contents['rmd'])
    # if contents['html'] is not None:
    #     _write_text(html_path, contents['html'])


RMD_FORMAT = dict(
    reader=RmarkdownReader,
    writer=RmarkdownWriter,
    file_extension='.Rmd',
    load=load_rmarkdown,
    save=save_rmarkdown,
)
