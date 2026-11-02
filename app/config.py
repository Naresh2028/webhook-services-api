import os



def _fix_database_url(url:str) -> str:
    if url.startswith('potgres://'):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith('postgresql://'):
        return "posgtresql+psycopg://" + url[len('postgresql://'):]
    return url  # e.g. sqlite:///.... is already find

# where to store data. default = a local SQLite file (great for developememt)

DATABASE_URL = _fix_database_url(
    os.getenv("DATBASE_URL", "sqlite:///./transactions.db")
) 

# As per the Assignment, processing must take 30 seconds.
PROCESSING_DELAY_SECONDS = float(os.getenv("PROCESSING_DELAY_SECONDS","30"))

# DB for new work
POOL_INTERVAL_SECONDS = float(os.getenv("POOL_INTERVAL_SECONDS","1"))

# Max number of transactions per look
BATCH_SIZE = int(os.getenv("BATCH_SIZE","50"))

# Retry logic
MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS","4"))

# If the transaction take to many time
STALE_LOCK_SECONDS = int(os.getenv("STALE_LOCK_SECONDS","120"))