import csv
import os
from typing import List


class BaseLogger:
    """Base singleton logger that stores entries in memory and dumps to CSV.

    Each concrete subclass maintains its own singleton instance and writes
    to its own CSV file. Entries are stored as comma-separated strings;
    :meth:`dump_to_csv` splits on ``,`` to produce rows.

    Attributes:
        entries: Accumulated log lines, one string per entry.
        filename: Output CSV file path written by :meth:`dump_to_csv`.
    """

    _instance = None
    filename = "base_log.csv"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.entries: List[str] = []
        return cls._instance

    def log(self, msg: str) -> None:
        """Append *msg* to the in-memory log and print it.

        Args:
            msg: The log line to store and display.
        """
        self.entries.append(msg)
        print(msg)

    def dump_to_csv(self) -> None:
        """Write all accumulated entries to :attr:`filename` as CSV rows.

        Each stored string is split on ``,`` to form a row. Existing file
        contents are overwritten.
        """
        with open(os.path.join("output", self.filename), "w", newline="") as f:
            writer = csv.writer(f)
            for line in self.entries:
                writer.writerow([cell.strip() for cell in line.split(",")])
