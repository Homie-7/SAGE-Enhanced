"""Test-session setup.

Must run before any test module imports app.config, which loads .env at
import time. Without this, a developer's real .env (VAL_API_KEY,
SAGE_ADMIN_MODE, etc.) leaks into the whole pytest process and produces
order-dependent failures.
"""

import os

os.environ.setdefault("SAGE_SKIP_DOTENV", "1")
