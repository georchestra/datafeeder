# Apache Airflow base image (Debian Trixie)

Apache only publishes `apache/airflow` images based on Debian **bookworm**. To run
Airflow on Debian **Trixie** we build the base image ourselves from the **official
Airflow Dockerfile**, which compiles Python from source on top of a `debian:*-slim`
base image (build arg `BASE_IMAGE`).

## Contents
- `Dockerfile` — verbatim copy of the official Airflow Dockerfile, tag `3.2.2`
  (https://raw.githubusercontent.com/apache/airflow/3.2.2/Dockerfile).
- `scripts/docker/keys/` — apt/Python signing keys referenced by the Dockerfile,
  copied from the same tag.

## Build
```bash
make build-airflow-base
# equivalent to:
docker build \
  --build-arg BASE_IMAGE=debian:trixie-slim \
  --build-arg AIRFLOW_VERSION=3.2.2 \
  --build-arg AIRFLOW_PYTHON_VERSION=3.14.0 \
  -t datafeeder-airflow-base:3.2.2-trixie \
  docker/airflow-base
```

The resulting `datafeeder-airflow-base:3.2.2-trixie` image is consumed as the `base`
stage of `docker/Dockerfile.airflow` (build arg `AIRFLOW_BASE_IMAGE`).

## Upgrading
1. Download the official Dockerfile and `scripts/docker/keys/` for the new tag.
2. Bump `AIRFLOW_VERSION` / `AIRFLOW_PYTHON_VERSION` in the `Makefile` and
   `apps/elt/pyproject.toml`, then regenerate `apps/elt/uv.lock`.

## Trixie patch
Two minimal changes are applied to the upstream `DEV_APT_DEPS` list for Trixie
compatibility (re-apply them when refreshing from upstream):
- removed `lzma-dev`: bookworm-only transitional package, gone on Trixie and
  fully covered by `liblzma-dev`.
- removed `lcov`: on Trixie it depends on the system Python (`libpython3.13`),
  which the official Dockerfile forbids (Python is compiled from source). `lcov`
  is only a coverage tool and is not needed to build/run the image.
