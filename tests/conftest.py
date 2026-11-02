import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["PROCESSING_DELAY_SECONDS"] = "1"
os.environ["POLL_INTERVAL_SECONDS"] = "0.2"