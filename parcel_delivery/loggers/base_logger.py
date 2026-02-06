import csv


class BaseLogger:
    _instance = None
    filename = "base_log.csv"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.entries = []
        return cls._instance

    def log(self, msg):
        self.entries.append(msg)
        print(msg)

    def dump_to_csv(self):
        # Save to CSV
        with open(self.filename, "w", newline="") as f:
            writer = csv.writer(f)
            for line in self.entries:
                # Split by comma to make it a row
                row = line.split(",")
                writer.writerow(row)