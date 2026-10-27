# New in this fork. The reference repo's AIHawkJobManager.write_to_file()
# re-reads and re-writes the ENTIRE json array on every single job (O(n^2)
# over a big scrape) and a crash mid-write corrupts the whole file. This
# writer instead appends one JSON object per line and flushes immediately,
# so a crash only ever loses the in-progress line, not the whole dataset.

from pathlib import Path

from src.job import Job


class JsonlWriter:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(self.path, "a", encoding="utf-8")

    def __call__(self, job: Job) -> None:
        self._fh.write(job.to_json_line() + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()
