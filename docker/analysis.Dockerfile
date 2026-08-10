# Self-contained image for Part A of this artifact: it rebuilds every table and
# figure in the paper from the shipped result CSVs.
#
# It needs no network at run time and executes no tests. The expensive test
# execution lives in the other image (docker/Dockerfile, Part B).
#
#   docker build -f docker/analysis.Dockerfile -t shaker/analysis .
#   docker run --rm -v "$PWD/output:/out" shaker/analysis
#
# or simply:  ./run_analysis.sh
#
# Results land in ./output/generated/*.tex and ./output/img/*.png on the host.

FROM python:3.11-slim

# Pinned so that the numbers this image produces stay reproducible over time.
# The versions the artifact was last verified with are recorded in README.md.
COPY analysis/requirements-lock.txt /tmp/requirements-lock.txt
RUN pip install --no-cache-dir -r /tmp/requirements-lock.txt

WORKDIR /artifact

# Only what the analysis reads. No test execution, no subject projects.
COPY analysis/ /artifact/analysis/
COPY dataset/  /artifact/dataset/
COPY results/  /artifact/results/
COPY README.md LICENSE /artifact/

# The analysis scripts write to <artifact-root>/paper/{generated,img}. Make that
# the bind-mounted output directory, so results appear on the host and nothing
# has to be written into the image. Created at build time so the container also
# works when run as a non-root user (docker run -u ...).
RUN mkdir -p /out && ln -s /out /artifact/paper

# Writable by any uid, so `-u $(id -u):$(id -g)` works for matplotlib's cache.
ENV MPLCONFIGDIR=/tmp/matplotlib \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY docker/run_analysis_in_container.sh /run_analysis_in_container.sh
RUN chmod +x /run_analysis_in_container.sh

ENTRYPOINT ["/run_analysis_in_container.sh"]
