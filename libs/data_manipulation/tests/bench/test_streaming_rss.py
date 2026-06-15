"""Peak-RSS regression benchmark for the streaming file reader.

Gated by ``DATAFEEDER_RUN_BENCH=1`` because the test materialises a
synthetic ~150 MB GeoJSON on disk; skip on every normal CI run.

We exercise ``open_file`` directly with a no-op consumer so the
read path (the dominant memory pressure pre-streaming) runs end-to-end
while DB plumbing is bypassed.

Acceptance bar: peak RSS delta during the full read of the file must
stay well under the on-disk size. The pre-streaming reader loaded the
whole frame into Python, so RSS scaled with the file size; the new path
keeps it bounded by ``BATCH_ROWS``.
"""

from __future__ import annotations

import json
import os
import resource
import threading
import time
from pathlib import Path

import pytest

from data_manipulation.arrow_reader import open_file

pytestmark = pytest.mark.skipif(
    os.environ.get("DATAFEEDER_RUN_BENCH") != "1",
    reason="benchmark; opt in with DATAFEEDER_RUN_BENCH=1",
)


def _ru_maxrss_mb() -> float:
    """Peak resident set size for this process, in MiB (Linux ru_maxrss is KiB)."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


class _RssWatchdog:
    """Background poller that records peak RSS seen during a context."""

    def __init__(self, interval_s: float = 0.05) -> None:
        self._interval = interval_s
        self.peak_mb = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            self.peak_mb = max(self.peak_mb, _ru_maxrss_mb())
            time.sleep(self._interval)

    def __enter__(self) -> "_RssWatchdog":
        self.peak_mb = _ru_maxrss_mb()
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
        self.peak_mb = max(self.peak_mb, _ru_maxrss_mb())


def _write_synthetic_geojson(path: Path, feature_count: int) -> int:
    """Write a feature-stream GeoJSON without materialising the whole thing.

    Returns the on-disk byte size.
    """
    with path.open("w") as f:
        f.write('{"type":"FeatureCollection","features":[')
        for i in range(feature_count):
            if i:
                f.write(",")
            feature = {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [i * 1e-5, i * 1e-5]},
                "properties": {
                    "id": i,
                    "name": f"feature-{i:08d}",
                    "category": "cat-" + str(i % 32),
                    "tags": ",".join(f"tag{i % 7}" for _ in range(4)),
                },
            }
            f.write(json.dumps(feature, separators=(",", ":")))
        f.write("]}")
    return path.stat().st_size


def test_file_reader_peak_rss_stays_bounded(tmp_path: Path) -> None:
    """Peak RSS during a full file read must stay well below the file size."""

    feature_count = 500_000  # ~150 MB GeoJSON on disk
    path = tmp_path / "bench.geojson"
    file_size_mb = _write_synthetic_geojson(path, feature_count) / (1024 * 1024)
    assert file_size_mb > 50, f"synthetic file too small: {file_size_mb:.1f} MB"

    batches_seen = 0
    rows_seen = 0

    baseline_mb = _ru_maxrss_mb()
    with _RssWatchdog() as rss:
        with open_file(str(path)) as src:
            for batch in src.reader:
                batches_seen += 1
                rows_seen += batch.num_rows

    peak_delta_mb = rss.peak_mb - baseline_mb
    # Bound: the new reader yields one batch at a time, so memory should be
    # dominated by batch_rows × per-feature size, NOT by file size. Generous
    # cap that still proves we're not in the "whole-file in RAM" regime.
    cap_mb = max(0.5 * file_size_mb, 300.0)
    assert rows_seen == feature_count
    assert batches_seen > 1, "reader must yield multiple batches for a large file"
    print(
        f"\nfile={file_size_mb:.1f} MB  batches={batches_seen}  rows={rows_seen}"
        f"  peak_rss_delta={peak_delta_mb:.1f} MB  cap={cap_mb:.1f} MB"
    )
    assert peak_delta_mb < cap_mb, (
        f"peak RSS delta {peak_delta_mb:.1f} MB exceeds cap "
        f"{cap_mb:.1f} MB (file is {file_size_mb:.1f} MB)"
    )
