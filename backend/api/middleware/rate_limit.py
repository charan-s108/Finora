import os

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[
        f"{os.getenv('RATE_LIMIT_PER_MINUTE', '20')}/minute",
        f"{os.getenv('RATE_LIMIT_PER_HOUR', '200')}/hour",
    ],
)
