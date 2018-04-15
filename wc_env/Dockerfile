# :Author: Jonathan Karr <karr@mssm.edu>
# :Date: 2017-11-13
# :Copyright: 2017, Karr Lab
# :License: MIT

# base
FROM ubuntu:latest

# install apt packages
RUN apt-get update -y && \
    apt-get install -y \
    build-essential \
    ca-certificates \
    cmake \
    default-jre \
    enchant \
    expect \
    git \
    graphviz \
    gzip \
    locales \
    libbz2-dev \
    libcairo2-dev \
    libeigen3-dev \
    libffi6 \
    libffi-dev \
    libglpk-dev \
    libjpeg-dev \
    libmysqlclient-dev \
    libmysqld-dev \
    libsqlite3-dev \
    libssl-dev \
    libxml2-dev \
    mercurial \
    nano \
    openssl \
    pandoc \
    ssh \
    sudo \
    swig \
    tar \
    tk8.5-dev \
    vim \
    wget \
    zip \
    zlib1g-dev

# set locale
RUN locale-gen en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

# install Python 2, 3
ARG version_py2=2.7.14
ARG version_py3=3.6.4
ENV LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/usr/local/lib
RUN apt-get install -y tk-dev \
    \
    && cd /tmp \
    && wget https://www.python.org/ftp/python/${version_py2}/Python-${version_py2}.tgz -O /tmp/Python-${version_py2}.tgz \
    && tar xzf /tmp/Python-${version_py2}.tgz \
    && cd /tmp/Python-${version_py2} \
    && ./configure --prefix=/usr/local --enable-optimizations --enable-shared --enable-unicode=ucs4 \
    && make \
    # && make test \
    && make install \
    && ldconfig \
    && python2.7 -m ensurepip \
    && cd / \
    && rm -r /tmp/Python-${version_py2}.tgz \
    && rm -r /tmp/Python-${version_py2} \
    \
    && cd /tmp \
    && wget https://www.python.org/ftp/python/${version_py3}/Python-${version_py3}.tgz -O /tmp/Python-${version_py3}.tgz \
    && tar xzf /tmp/Python-${version_py3}.tgz \
    && cd /tmp/Python-${version_py3} \
    && ./configure --prefix=/usr/local --enable-optimizations --enable-shared --enable-unicode=ucs4 \
    && make \
    # && make test \
    && make install \
    && ldconfig \
    && python3.6 -m ensurepip \
    && cd / \
    && rm -r /tmp/Python-${version_py3}.tgz \
    && rm -r /tmp/Python-${version_py3}

# install openbabel
ARG version_openbabel=2.4.1
RUN cd /tmp \
    && version_openbabel_dash=$(echo $version_openbabel | sed 's/\./-/g') \
    && wget https://github.com/openbabel/openbabel/archive/openbabel-${version_openbabel_dash}.tar.gz -O /tmp/openbabel-${version_openbabel}.tar.gz \
    && tar -xvvf /tmp/openbabel-${version_openbabel}.tar.gz \
    && cd openbabel-openbabel-${version_openbabel_dash} \
    && mkdir build \
    && cd build \
    && cmake .. \
    && make \
    # && make test \
    && make install \
    && ldconfig \
    && cd / \
    && rm -r /tmp/openbabel-${version_openbabel}.tar.gz \
    && rm -r /tmp/openbabel-openbabel-${version_openbabel_dash}

# install xpress
# ARG version_xpress=8.4.4
# ARG xpress_license_server=
# COPY tokens/xpauth.xpr /tmp/xpauth.xpr
# COPY assets/xpress.egg-info /tmp/xpress.egg-info
# RUN cd /tmp \
#     && wget https://clientarea.xpress.fico.com/downloads/${version_xpress}/xp${version_xpress}_linux_x86_64_setup.tar \
#     && mkdir xp${version_xpress}_linux_x86_64_setup \
#     && tar -xvvf xp${version_xpress}_linux_x86_64_setup.tar -C xp${version_xpress}_linux_x86_64_setup \
#     && cd /tmp/xp${version_xpress}_linux_x86_64_setup \
#     && ./install.sh -l floating-client -a /tmp/xpauth.xpr -d /opt/xpressmp -k yes -s ${xpress_license_server} \
#     && echo "/opt/xpressmp/lib" | tee /usr/local/lib/python2.7/site-packages/xpress.pth \
#     && echo "/opt/xpressmp/lib" | tee /usr/local/lib/python3.6/site-packages/xpress.pth \
#     && cp /tmp/xpress.egg-info /usr/local/lib/python2.7/site-packages/xpress-${version_xpress}.egg-info \
#     && cp /tmp/xpress.egg-info /usr/local/lib/python3.6/site-packages/xpress-${version_xpress}.egg-info \
#     && cd /tmp \
#     && rm /tmp/xp${version_xpress}_linux_x86_64_setup.tar \
#     && rm -r /tmp/xp${version_xpress}_linux_x86_64_setup \
#     && rm /tmp/xpauth.xpr \
#     && rm /tmp/xpress.egg-info
# ENV XPRESSDIR=/opt/xpressmp
# ENV PATH=$PATH:$XPRESSDIR/bin
# ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/lib/x86_64-linux-gnu:$XPRESSDIR/lib
# ENV CLASSPATH=$CLASSPATH:$XPRESSDIR/lib/xprs.jar:$XPRESSDIR/lib/xprb.jar:$XPRESSDIR/lib/xprm.jar
# ENV XPRESS=$XPRESSDIR/bin

# COIN-OR: CBC (latest version compatible with CyLP)
# ARG version_cbc=2.8.5
# RUN cd /tmp \
#     && wget https://www.coin-or.org/download/source/Cbc/Cbc-${version_cbc}.tgz \
#     && tar -xvvf Cbc-${version_cbc}.tgz \
#     && cd Cbc-${version_cbc} \
#     && mkdir build \
#     && cd build \
#     && mkdir -p /opt/coin-or/cbc \
#     && ../configure -C --prefix=/opt/coin-or/cbc --enable-gnu-packages \
#     && make \
#     # && make test \
#     && make install \
#     && cd ../../ \
#     && rm -r Cbc-${version_cbc} \
#     && rm Cbc-${version_cbc}.tgz
# ENV COIN_INSTALL_DIR=/opt/coin-or/cbc
# ENV PATH=${PATH}:/opt/coin-or/cbc/bin
# ENV LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/opt/coin-or/cbc/lib

# # COIN-OR: coinutils
# ARG version_coin_utils=2.10.14
# RUN cd /tmp \
#     && wget https://www.coin-or.org/download/source/CoinUtils/CoinUtils-${version_coin_utils}.tgz \
#     && tar -xvvf CoinUtils-${version_coin_utils}.tgz \
#     && cd CoinUtils-${version_coin_utils} \
#     && mkdir build \
#     && cd build \
#     && mkdir -p /opt/coin-or/coinutils \
#     && ../configure -C --prefix=/opt/coin-or/coinutils --enable-gnu-packages \
#     && make \
#     # && make test \
#     && make install \
#     && cd /tmp \
#     && rm -r CoinUtils-${version_coin_utils} \
#     && rm CoinUtils-${version_coin_utils}.tgz
# ENV PATH=${PATH}:/opt/coin-or/coinutils/bin
# ENV LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/opt/coin-or/coinutils/lib
#
# # install qpOASES
# ARG version_qpoases=3.2.1
# RUN cd /tmp \
#     && wget https://www.coin-or.org/download/source/qpOASES/qpOASES-${version_qpoases}.tgz \
#     && tar -xvvf qpOASES-${version_qpoases}.tgz \
#     && cd qpOASES-${version_qpoases} \
#     && make \
#     # && make test \
#     && mkdir -p /opt/coin-or/qpoases/lib \
#     && cp bin/libqpOASES.* /opt/coin-or/qpoases/lib \
#     && cp -r include/ /opt/coin-or/qpoases \
#     && cd interfaces/python \
#     && pip2.7 install cython numpy \
#     && pip3.6 install cython numpy \
#     && python2.7 setup.py install \
#     && python3.6 setup.py install \
#     && cd /tmp \
#     && rm -r qpOASES-${version_qpoases} \
#     && rm qpOASES-${version_qpoases}.tgz
# ENV LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/opt/coin-or/qpoases/lib

# kallisto
# ARG version_kallisto=0.44.0
# RUN cd /tmp \
#     && wget https://github.com/pachterlab/kallisto/releases/download/v${version_kallisto}/kallisto_linux-v${version_kallisto}.tar.gz \
#     && tar -xvvf kallisto_linux-v${version_kallisto}.tar.gz \
#     && cp kallisto_linux-v${version_kallisto}/kallisto /usr/local/bin \
#     && rm -rf kallisto_linux-v${version_kallisto} \
#     && rm -rf kallisto_linux-v${version_kallisto}.tar.gz

# Docker
# RUN apt-get update \
#     && apt-get install -y \
#         apt-transport-https \
#         ca-certificates \
#         curl \
#         software-properties-common \
#     && curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add - \
#     && add-apt-repository \
#         "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
#         $(lsb_release -cs) \
#         stable" \
#     && apt-get update \
#     && apt-get install -y docker-ce

# CircleCI local build agent
# RUN curl -o /usr/local/bin/circleci https://circle-downloads.s3.amazonaws.com/releases/build_agent_wrapper/circleci \
#     && chmod +x /usr/local/bin/circleci

# Install Python packages; pbr has to be installed first to workaround error in sphinxcontrib-spelling installation
COPY tmp/requirements.txt /tmp/
RUN pip3.6 install -U pip setuptools \
    && pip3.6 install -U \
        cython \
        et3 \
        ipython \
        mock \
        numpy \
        pbr \
        pypandoc \
        requests \
        six \
    && pip3.6 install -r /tmp/requirements.txt \
    \
    && rm tmp/requirements.txt
COPY assets/matplotlibrc /root/.config/matplotlib/matplotlibrc

# RUN python2.7 -c "import ete3; ete3.NCBITaxa().get_descendant_taxa('Homo');" && \
#    python3.6 -c "import ete3; ete3.NCBITaxa().get_descendant_taxa('Homo');"

# configure git
RUN \
  echo '[url "ssh://git@github.com/"]\n\
    insteadOf = https://github.com/' > ~/.gitconfig \
  && mkdir -p ~/.ssh \
  && ssh-keyscan github.com >> ~/.ssh/known_hosts

# final command
CMD bash
