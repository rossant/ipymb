FROM ipython/scipystack

RUN pip install mistune

# Install from source based on #7278
RUN mkdir -p /tmp/minrk
WORKDIR /tmp/minrk
RUN git clone https://github.com/minrk/ipython.git
WORKDIR /tmp/minrk/ipython
RUN git checkout -b nb-file-ext
RUN git pull origin nb-file-ext
RUN git submodule init
RUN git submodule update
RUN python3 setup.py install


# Install ipymd on the imaage and add it to PYTHONPATH
RUN mkdir -p /usr/src
ADD . /usr/src
ENV PYTHONPATH /usr/src

# Set up the PYTHONPATH info
RUN ipython profile create
RUN echo "c.NotebookApp.contents_manager_class = 'ipymd.AtlasContentsManager'" >> /root/.ipython/profile_default/ipython_notebook_config.py

# set workdir and start server
WORKDIR /usr/data
CMD ipython3 notebook --ip=0.0.0.0 --no-browser
