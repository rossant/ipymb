# -*- coding: utf-8 -*-


"""Rmarkdown readers and writers.

"""

# ------------------------------------------------------------------------------
# Imports
# ------------------------------------------------------------------------------

import re
import os.path

import json
import pypandoc
from html import escape as html_escape

try:
    import nbformat as nbf
    from nbformat.v4.nbbase import validate
except ImportError:
    import IPython.nbformat as nbf
    from IPython.nbformat.v4.nbbase import validate

from jinja2 import Environment, PackageLoader, select_autoescape, Markup

from ..utils.utils import _read_text, _write_text, _get_cell_types, \
    _ensure_string
from ..lib.rmarkdown import _option_value_str, _parse_chunk_meta, \
    _merge_consecutive_markdown_cells, _is_code_chunk, HtmlNbChunkCell, \
    _get_nb_html_path, _b64_encode
from ..lib.notebook import _stream_output_to_result
from .markdown import BaseMarkdownReader, BaseMarkdownWriter
from ipymd.core.format_manager import convert
from ..ext.six import StringIO


# ------------------------------------------------------------------------------
# R Markdown
# ------------------------------------------------------------------------------


class RmarkdownReader(object):
    """ read R notebook format (combine .Rmd and .nb.html).
    Output format is a jupyter nbformat object.

    Unlike all other ipymd readers, this class uses the jupyter nbformat
    as internal representation of the notebook. The jupyter format was chosen
    as internal format to enable more complex outputs
    (i.e. multiple outputs per cell, including multiple images)"""

    def __init__(self):
        self._rmd_reader = RmdReader()
        self._html_nb_reader = HtmlNbReader()

    def read(self, contents):
        cells_rmd = self._rmd_reader.read(contents['rmd'])
        nb_html = self._html_nb_reader.read(contents['html'])
        # we need both inputs in jupyter nb format, so we can merge them.
        nb_rmd = convert(cells_rmd, to='notebook')

        nb_rmd['cells'] = _merge_consecutive_markdown_cells(nb_rmd['cells'])
        nb_html['cells'] = _merge_consecutive_markdown_cells(nb_html['cells'])

        nb_merged = self._merge_notebooks(nb_rmd, nb_html)
        validate(nb_merged)
        return nb_merged

    def _merge_notebooks(self, nb_rmd, nb_html):
        # if not consistent, discard output (do not consider html cells)
        if self._check_notebook_consistency(nb_rmd['cells'], nb_html['cells']):
            for rmd_cell, html_cell in zip(nb_rmd['cells'], nb_html['cells']):
                if 'outputs' in html_cell:
                    rmd_cell['outputs'] = html_cell['outputs']
        return nb_rmd

    def _check_notebook_consistency(self, rmd_cells, html_cells):
        """The lists of cells are considered consistent if the cell
        types appear in the same order. """
        return _get_cell_types(rmd_cells) == _get_cell_types(html_cells)


class RmdReader(BaseMarkdownReader):
    """Read RMarkdown .Rmd files"""
    def __init__(self):
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
        r'<img src="data:(.*?);base64,([\s\S]*?)" />'
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
            assert start_tag == end_tag, \
                "text and chunk blocks must not be nested."
            yield start_tag, contents.strip()

    def _parse_image(self, html):
        try:
            mime, data = next(iter(self.def_image_element.findall(html)))
        except StopIteration:
            mime = 'text/plain'
            data = 'IPYMD: Error reading image.'
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
        cell = HtmlNbChunkCell(self._count)
        self._count += 1

        for start_tag, b64, contents, end_tag in self.def_chunk_element.findall(chunk_block):
            assert start_tag == end_tag, \
                "different chunk elements must not be nested. "
            b64 = b64.strip()
            contents = contents.strip()
            if start_tag == 'source':
                # we ignore the source as we obtain it from .Rmd
                pass
            elif start_tag in ['output', 'warning', 'error', 'message']:
                assert cell is not None, "output without source"
                cell.new_output(start_tag, b64)
            elif start_tag == 'plot':
                assert cell is not None, "plot without source"
                mime, data = self._parse_image(contents)
                cell.new_plot(mime, data, b64)

        return cell.cell


class RmarkdownWriter(object):
    """Write R notebook (combine .Rmd and .nb.html) """

    def __init__(self):
        self._rmd_writer = RmdWriter()
        self._nb_html_writer = NbHtmlWriter(self._rmd_writer)

    def write_contents(self, nb):
        """convert a jupyter notebook dict to rmarkdown"""
        # Parsing the notebook using nbf will get rid of the
        # multi line strings.
        # nb = nbf.from_dict(nb)
        assert nb['nbformat'] >= 4

        self.write_notebook_metadata(nb['metadata'])
        for cell in nb['cells']:
            self.write(cell)

    def write(self, cell):
        self._rmd_writer.write(cell)
        self._nb_html_writer.write(cell)

    def write_notebook_metadata(self, metadata):
        # metadata = json.loads(json.dumps(metadata))
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


class RmdWriter(BaseMarkdownWriter):
    """Default .Rmd writer."""

    def __init__(self):
        super(RmdWriter, self).__init__()

    def append_code(self, input, output=None, metadata=None):
        input = _ensure_string(input)
        self._output.write(self._code_block(input, metadata))

    @staticmethod
    def _code_block(code, meta):
        return '```{{{meta}}}\n{code}\n```'.format(
            meta=RmdWriter._encode_metadata(meta), code=code.rstrip())

    def append_markdown(self, source, metadata):
        source = _ensure_string(source)
        if metadata is not None and len(metadata) > 0:
            raise RuntimeWarning("Metadata for markdown cells is currently"
                                 "not supported.")
        self._output.write(source.rstrip())

    @staticmethod
    def _encode_metadata(metadata):
        def encode_option(key, value):
            return "{}={}".format(key, _option_value_str(value))

        if metadata is not None:
            # TODO derive default lang from kernel
            lang = metadata.pop('lang', 'python')
            name = metadata.pop('name', None)
            options = ", ".join(encode_option(k, v)
                                for k, v in metadata.items())

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

    def write(self, cell):
        """Write a ipynb cell to markdown"""
        metadata = cell.get('metadata', None)
        if cell['cell_type'] == 'markdown':
            self.append_markdown(cell['source'], metadata)
        elif cell['cell_type'] == 'code':
            # output is not handled by RmdReader
            self.append_code(cell['source'], output=None, metadata=metadata)
        self._new_paragraph()

    @property
    def contents(self):
        return self._output.getvalue().rstrip() + '\n'  # end of file \n


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
        self._output = StringIO()

    @property
    def template(self):
        """ Load the jinja2 template from the package resources. """
        env = Environment(
            loader=PackageLoader('ipymd', 'ressources'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        return env.get_template('r_notebook.template.html')

    def append_markdown(self, markdown, metadata):
        markdown = _ensure_string(markdown)
        html = pypandoc.convert_text(markdown, 'html', format='md')
        self._output.write(self._create_tag('text', html, metadata) + "\n")

    def append_code(self, source, outputs, metadata):
        source = _ensure_string(source)

        # Markdown representation of code is given as b64 in nb.html
        # TODO derive default lang from kernel
        lang = metadata.get('lang', 'python')
        source_as_markdown = BaseMarkdownWriter.format_code(source, lang)

        child_tags = []
        child_tags.append(
            self._create_tag('source',
                             tag_content=self._format_source(source, metadata),
                             tag_meta={'data': source_as_markdown})
        )
        for output in outputs:
            child_tags.extend(self._create_output_tag(output))

        self._output.write(
            self._create_tag('chunk', "\n".join(child_tags) + "\n") + "\n"
        )

    def _create_output_tag(self, output):
        """yield tags such as <!--rnb-plot-begin"""
        output = _stream_output_to_result(output)
        assert output['output_type'] in ['execute_result', 'display_data']
        # text first!
        try:
            text = _ensure_string(output['data'].pop('text/plain'))
            yield self._create_tag('output',
                                   tag_content=self._format_text_output(text),
                                   tag_meta={'data': text})
        except KeyError:
            pass

        # then images...
        for mime, data in output['data'].items():
            if mime.startswith('image/'):
                yield self._create_tag('plot',
                                       tag_content=self._format_image(
                                           mime, data),
                                       tag_meta=output['metadata'])
            else:
                raise RuntimeError("Invalid output mime-type: {}".format(mime))

    @staticmethod
    def _format_source(source, metadata):
        """Format contents of source tag. """
        # TODO default lang?
        lang = metadata.get('lang', 'raw')
        return '<pre class="{lang}"><code>{source}</code></pre>'.format(
            lang=lang, source=html_escape(source)
        )

    @staticmethod
    def _format_image(mime, data):
        return '<p><img src="data:{mime};base64,{data}" /></p>'.format(
            mime=mime, data=data)

    @staticmethod
    def _format_text_output(text):
        return "<pre><code>{}</code></pre>".format(text)

    @staticmethod
    def _create_tag(tag_name, tag_content, tag_meta=None):
        """

        Parameters
        ----------
        tag_name: str
            e.g. text, chunk, ... like in <!-- rnb-text-begin -->
        tag_meta: dict
            meta-dictionary which can be added to the tag.
            Will be base64 encoded. Example <!-- rnb-source-begin eyJkXR== -->
        tag_content:
            html content which will be enclosed in the `begin` and `end` tags.

        Returns
        -------
        str
            <!-- rnb-tag-begin>some contents<!--rnb-tag-end-->\n

        """
        meta_b64 = "" if tag_meta is None or tag_meta == {} else _b64_encode(
            json.dumps(tag_meta))
        return "<!-- rnb-{tag}-begin {b64}-->\n" \
               "{contents}\n" \
               "<!-- rnb-{tag}-end -->".format(tag=tag_name, b64=meta_b64,
                                               contents=tag_content)

    def write(self, cell):
        metadata = cell.get('metadata', None)
        if cell['cell_type'] == 'markdown':
            self.append_markdown(cell['source'], metadata)
        elif cell['cell_type'] == 'code':
            self.append_code(cell['source'], cell['outputs'], metadata)

    @property
    def contents(self):
        base64_rmd = _b64_encode(self._rmd_writer.contents)
        html_nb = Markup(self._output.getvalue().rstrip() + '\n')
        # TODO is the filename in javascript necessary for anything_
        # the writer does not know anything about the filename
        # therefore we use a hardcoded filename as workaround.
        filename = "notebook.Rmd"
        return self.template.render(filename=filename,
                                    html_nb=html_nb,
                                    base64_rmd=base64_rmd)


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
    if contents['html'] is not None:
        _write_text(html_path, contents['html'])


RMD_FORMAT = dict(
    reader=RmarkdownReader,
    writer=RmarkdownWriter,
    file_extension='.Rmd',
    load=load_rmarkdown,
    save=save_rmarkdown,
)
