from mambaorg/micromamba

# preload virtual environment that we'll definitely need
# this way we usually won't need to fetch packges every update
ARG MAMBA_DOCKERFILE_ACTIVATE=1
RUN micromamba create -y -n isccp -c conda-forge satpy numpy tqdm pandas xarray netcdf4 cartopy pyresample pysolar zstandard

WORKDIR /home/mambauser/
USER root
RUN apt update && apt install -y vim git
ADD tar/archive.tar isccp_l1g
RUN chown -R mambauser isccp_l1g
USER mambauser
RUN mkdir dat scratch && ln -s /home/mambauser/dat isccp_l1g/dat
ENV TMPDIR=/home/mambauser/scratch
ADD tar/coord_descent.tar isccp_l1g/
ADD tar/xrit.tar isccp_l1g/
COPY himawari-1.0-cp311-cp311-linux_x86_64.whl himawari-1.0-cp311-cp311-linux_x86_64.whl
RUN /opt/conda/envs/isccp/bin/pip install himawari-1.0-cp311-cp311-linux_x86_64.whl && rm himawari-1.0-cp311-cp311-linux_x86_64.whl
COPY init.sh init.sh

