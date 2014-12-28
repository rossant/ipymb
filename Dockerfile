FROM ipython/scipystack

RUN pip install mistune

# Install ipymd on the imaage and add it to PYTHONPATH
RUN mkdir -p /usr/src
ADD . /usr/src
ENV PYTHONPATH /usr/src

# Set up the PYTHONPATH info
RUN ipython profile create
RUN echo "c.NotebookApp.contents_manager_class = 'ipymd.AtlasContentsManager'" >> /root/.ipython/profile_default/ipython_notebook_config.py

# set workdir and start server
WORKDIR /usr/data
CMD ipython notebook --ip=0.0.0.0 --no-browser
