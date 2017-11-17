"""Test helper functions for comparing ipynb notebooks. """
from ipymd.utils.utils import _ensure_string


def _cell_source(cell):
    """Return the input of an ipynb cell."""
    return _ensure_string(cell.get('source', []))


def _cell_outputs(cell):
    """Return the output of an ipynb cell."""
    outputs = cell.get('outputs', [])
    return outputs


def _stream_output_to_result(output):
    """Convert a 'stream' output cell to an 'execute_result' cell. """
    if output['output_type'] == 'stream':
        return {
            'output_type': 'execute_result',
            'metadata': {},
            'data': {'text/plain': _ensure_string(output['text']).rstrip()},
            'execution_count': None
        }
    else:
        return output


def _output_ensure_string(*args):
    """make sure that strings split up as a list are coerced into a
    single string. """
    for output in args:
        for mime, out in output.get('data', {}).items():
            output['data'][mime] = _ensure_string(out)


def _assert_dict_key_equals(field, dict0, dict1):
    """assert that a field does either not exist in both
    dictionaries or is equal"""
    KEY_DOESNT_EXIST = object()
    assert dict0.get(field, KEY_DOESNT_EXIST) \
        == dict1.get(field, KEY_DOESNT_EXIST)


def _assert_cell_outputs_equal(output_0, output_1, check_metadata=True):
    output_0 = _stream_output_to_result(output_0)
    output_1 = _stream_output_to_result(output_1)
    _output_ensure_string(output_0, output_1)

    fields_to_check = ['output_type', 'data', 'ename', 'evalue', 'traceback']
    if check_metadata:
        fields_to_check.append('metadata')

    for field in fields_to_check:
        _assert_dict_key_equals(field, output_0, output_1)

    if 'execution_count' in (set(output_0) | set(output_1)):
        assert output_0['execution_count'] == output_1['execution_count'] or \
            output_1['execution_count'] is None or \
            output_0['execution_count'] is None



def _assert_cells_equal(cell_0, cell_1, check_metadata=True,
                        check_outputs=True):
    assert cell_0['cell_type'] == cell_1['cell_type']
    assert _cell_source(cell_0) == _cell_source(cell_1)
    if check_outputs:
        outputs_0 = _cell_outputs(cell_0)
        outputs_1 = _cell_outputs(cell_1)
        assert len(outputs_0) == len(outputs_1)
        for output_0, output_1 in zip(outputs_0, outputs_1):
            _assert_cell_outputs_equal(output_0, output_1,
                                       check_metadata=check_metadata)


def _assert_notebooks_equal(nb_0, nb_1, check_notebook_metadata=True,
                            check_cell_metadata=True,
                            check_cell_outputs=True):
    if check_notebook_metadata:
        assert nb_0['metadata'] == nb_1['metadata']
    assert len(nb_0['cells']) == len(nb_1['cells'])
    for cell_0, cell_1 in zip(nb_0['cells'], nb_1['cells']):
        _assert_cells_equal(cell_0, cell_1, check_metadata=check_cell_metadata,
                            check_outputs=check_cell_outputs)


def _cell_input(cell):
    """Return the input of an ipynb cell."""
    return _ensure_string(cell.get('source', []))


def _cell_output(cell):
    """Return the output of an ipynb cell."""
    outputs = cell.get('outputs', [])
    # Add stdout.
    stdout = ('\n'.join(_ensure_string(output.get('text', ''))
                        for output in outputs)).rstrip()
    # Add text output.
    text_outputs = []
    for output in outputs:
        out = output.get('data', {}).get('text/plain', [])
        out = _ensure_string(out)
        # HACK: skip <matplotlib ...> outputs.
        if out.startswith('<matplotlib'):
            continue
        text_outputs.append(out)
    return stdout + '\n'.join(text_outputs).rstrip()
