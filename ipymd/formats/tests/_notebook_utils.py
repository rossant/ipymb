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


def _assert_cell_outputs_equal(output_0, output_1, check_metadata=True):
    output_0 = _stream_output_to_result(output_0)
    output_1 = _stream_output_to_result(output_1)
    assert output_0['output_type'] == output_1['output_type']
    assert output_0['data'] == output_1['data']
    assert output_0['execution_count'] == output_1['execution_count'] or \
        output_1['execution_count'] is None or \
        output_0['execution_count'] is None
    if check_metadata:
        assert output_0['metadata'] == output_1['metadata']


def _assert_cells_equal(cell_0, cell_1, check_metadata=True):
    assert cell_0['cell_type'] == cell_1['cell_type']
    assert _cell_source(cell_0) == _cell_source(cell_1)
    for output_0, output_1 in zip(_cell_outputs(cell_0), _cell_outputs(cell_1)):
        _assert_cell_outputs_equal(output_0, output_1, check_metadata=check_metadata)


def _assert_notebooks_equal(nb_0, nb_1, check_notebook_metadata=True, check_cell_metadata=True):
    if check_notebook_metadata:
        assert nb_0['metadata'] == nb_1['metadata']
    for cell_0, cell_1 in zip(nb_0['cells'], nb_1['cells']):
        _assert_cells_equal(cell_0, cell_1, check_metadata=check_cell_metadata)
