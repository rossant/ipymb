# IPython notebook & Markdown

**Currently WIP, experimental project, use at your own risks**

Use Markdown `.md` documents instead of `.ipynb` files in the IPython notebook. You keep code input and outputs, but not plots, metadata, or prompt numbers. This is useful when you write technical documents, blog posts, books, etc.

![image](https://cloud.githubusercontent.com/assets/1942359/5570181/f656a484-8f7d-11e4-8ec2-558d022b13d3.png)

## Why?

### IPython notebook

Pros:

* Excellent UI for executing code interactively *and* writing text

Cons:

* nbformat not really git-friendly (JSON, contains the outputs by default)
* cannot easily edit in a text editor


### Markdown

Pros:

* Simple ASCII format to write code and text
* Can be edited in any text editor
* Git-friendly

Cons:

* No UI to execute code interactively

## Workflow

* Write contents (text and code) in a Markdown `document.md`
    * either in the notebook UI, as usual, with Markdown cells and code cells (useful when working on code)
    * or in a text editor, using Markdown (useful when working on text)
* Only the Markdown cells and code cells (input + text outputs for now) are saved in the file
* Collaborators can work on the Markdown document using GitHub (branches, pull requests...), they don't need IPython. They can do everything from the GitHub web interface.

### Details

* A notebook code cell = Markdown code block with explicit `python` syntax highlighting (i.e. ```` ```python ````)
* If `add_prompt=True` (default in `MarkdownContentsManager`, but not in `AtlasContentsManager`), intput and text outputs are converted to:

  ```
  > print("Hello world")
  Hello world
  ```

* `md => nb => md` and `nb => md => nb` are not exactly the identity function:

    * `*italics*` is replaced by `_italics_`
    * extra line breaks are discarded
    * text output and text stdout ==> combined text output (stdout lines first, output lines last)


## Caveats

**WARNING**: this is an experimental module, there is a risk for data loss, so be careful!

* Renaming doesn't work yet (issue #4)
* New notebook doesn't work yet (issue #5)


## Installation

0. You need IPython 3.0 (or latest master) (with PR #7278) and mistune.
1. Put this repo in your PYTHONPATH.
2. Add this in your `ipython_notebook_config.py` file:

    ```python
    c.NotebookApp.contents_manager_class = 'ipymd.MarkdownContentsManager'
    ```

3. Now, you can open `.md` files in the notebook.

### Atlas

There is also experimental support for O'Reilly Atlas (thanks to @odewahn, see [this presentation](http://odewahn.github.io/publishing-workflows-for-jupyter/#1)).

* Math equations are automatically replaced by `<span class="math-tex" data-type="tex">{equation}</span>` tags.
* Code inputs are replaced by `<pre data-code-language="{lang}" data-executable="true" data-type="programlisting">{code}</pre>` tags.

This is handled transparently in the notebook UI, i.e. you can keep writing math in `$$` and code in code cells or Markdown code blocks.

To use the Atlas format, put this in your config file:

```python
c.NotebookApp.contents_manager_class = 'ipymd.AtlasContentsManager'
```

## Using Docker

You can also run this using Docker on a Mac (via boot2docker) or Linux.  (NB: you need docker and boot2docker 1.3+.  Also, it's set up by default using the AtlasContentsManager.) 

Run this command within the directory containing the notebooks you want to edit.  (Note that docker will pull down the entire image the first time you run this command, so it may take a while.):

```
docker run -it -p 8888:8888 -v $(pwd):/usr/data odewahn/ipymd
```

Once the container starts, open your browser:

* On a Mac, go to `192.168.59.103:8888`
* On Ubuntu, go to `127.0.0.1:8888`

The `-v` option will map your current local directory on your host to the `/usr/data` directory on the container.  Note that this volume mapping is currently not supported on Windows, although I hope Windows will be supported soon.

### Building the image yourself

If you want to hack on this project with Docker, you can build your own image like this:

```
docker build -t odewahn/ipymd .
```