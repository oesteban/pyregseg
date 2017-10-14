# Use Ubuntu Trusty LTS
FROM oesteban/regseg:latest

RUN apt-get update && \
    apt-get install -y --no-install-recommends git graphviz && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Installing and setting up miniconda
RUN curl -sSLO https://repo.continuum.io/miniconda/Miniconda2-latest-Linux-x86_64.sh && \
    bash Miniconda2-latest-Linux-x86_64.sh -b -p /usr/local/miniconda && \
    rm Miniconda2-latest-Linux-x86_64.sh

ENV PATH=/usr/local/miniconda/bin:$PATH \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Installing precomputed python packages
RUN conda install -c conda-forge -y openblas=0.2.19; \
    sync && \
    conda install -c conda-forge -y \
                     numpy=1.12.0 \
                     scipy=0.19.0 \
                     scikit-learn=0.18.1 \
                     matplotlib=2.0.0 \
                     pandas=0.19.2 \
                     libxml2=2.9.4 \
                     libxslt=1.1.29 \
                     sympy=1.0 \
                     statsmodels=0.8.0 \
                     dipy=0.11.0 \
                     traits=4.6.0 \
                     psutil=5.2.2 \
                     sphinx=1.5.4; \
    sync &&  \
    chmod +x /usr/local/miniconda/bin/* && \
    conda clean --all -y; sync && \
    pip install mayavi && \
    python -c "from matplotlib import font_manager"


WORKDIR /src/pyregseg
COPY requirements.txt /src/pyregseg
RUN pip install -r requirements.txt 

COPY . /src/pyregseg/
RUN pip install .[all]

WORKDIR /work
