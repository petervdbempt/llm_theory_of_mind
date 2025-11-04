from pathlib import Path

class TextLogger:
    def __init__(self, filepath: Path):
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self.file = open(self.filepath, "w", encoding="utf-8")

    def log(self, msg: str):
        self.file.write(msg + "\n")
        self.file.flush()  # ensures it appears immediately

    def close(self):
        self.file.close()