# Apache Airflow base image (Debian Trixie)

Apache only publishes `apache/airflow` images based on Debian **bookworm**. We need
Trixie because GDAL >= 3.13 from conda-forge (installed in `docker/Dockerfile.airflow`)
links against the *system* libstdc++ and requires `GLIBCXX_3.4.31` / `CXXABI_1.3.15`,
i.e. GCC 13+. Bookworm ships `libstdc++6` 12.2, so `ogr2ogr` installs fine there but
fails to load at runtime; Trixie ships 14.2, which is compatible.

So we build the base image ourselves from the official Airflow Dockerfile on top of a
`debian:*-slim` base image (build arg `BASE_IMAGE`).

## Contents
- `Dockerfile` — the official Airflow Dockerfile, tag `3.2.2`
  (https://raw.githubusercontent.com/apache/airflow/3.2.2/Dockerfile), plus the local
  patches listed under [Trixie patch](#trixie-patch).
- `scripts/docker/keys/` — apt/Python signing keys referenced by the Dockerfile,
  copied from the same tag.

## Build

```bash
make build-airflow-base
# equivalent to:
docker build \
  --build-arg BASE_IMAGE=debian:trixie-slim \
  --build-arg AIRFLOW_VERSION=3.2.2 \
  -t datafeeder-airflow-base:3.2.2-trixie \
  docker/airflow-base
```

Note that `AIRFLOW_PYTHON_VERSION` has no effect: the patched `install_python()` takes
Python from apt (see below), so the image gets whatever Trixie ships — currently 3.13.5,
which satisfies the workspace's `requires-python = "==3.13.*"`. Bumping the workspace to
3.14 therefore requires more than a build arg, since Trixie has no `python3.14` package.

The resulting `datafeeder-airflow-base:3.2.2-trixie` image is consumed as the `base`
stage of `docker/Dockerfile.airflow` (build arg `AIRFLOW_BASE_IMAGE`).

## Upgrading
1. Download the official Dockerfile and `scripts/docker/keys/` for the new tag.
2. Re-apply the three patches below.
3. Bump `AIRFLOW_VERSION` in the `Makefile` and `apps/elt/pyproject.toml`, then
   regenerate `apps/elt/uv.lock`.

## Trixie patch
Three changes are applied to the upstream Dockerfile (re-apply them when refreshing
from upstream):
- `install_python()` rewritten to install Python from apt instead of building it from
  source, with an early `return 0` keeping the original body below it as dead code.
  This is why `AIRFLOW_PYTHON_VERSION` is ignored and the Python version is whatever
  Trixie packages.
- removed `lzma-dev` from `DEV_APT_DEPS`: bookworm-only transitional package, gone on
  Trixie and fully covered by `liblzma-dev`.
- removed `lcov` from `DEV_APT_DEPS`: on Trixie it pulls in the system Python
  (`libpython3.13`). It is only a coverage tool and is not needed to build/run the
  image.
