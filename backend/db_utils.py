"""
Database utility functions for OptiSchema backend.
"""

import ssl
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def configure_ssl(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standardize SSL configuration for asyncpg connections.

    Converts string sslmode values ('require', 'prefer', 'disable') into
    the ssl context objects that asyncpg expects.

    Uses system CA certificates by default so cloud databases (RDS, Cloud SQL,
    Supabase) are verified properly. Falls back to unverified only for
    'prefer'/'allow' modes where the user explicitly accepts weaker security.
    """
    config = config.copy()
    sslmode = config.get('ssl')

    if sslmode in ('require', True):
        ctx = ssl.create_default_context()
        # Most cloud providers (RDS, Cloud SQL) use publicly trusted CAs,
        # so default context with system CAs works. If users have self-signed
        # certs they can set DATABASE_URL with sslmode=prefer as a workaround.
        config['ssl'] = ctx
    elif sslmode in ('prefer', 'allow'):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        config['ssl'] = ctx
    elif sslmode == 'disable':
        config['ssl'] = False
    elif sslmode and sslmode is not False:
        # Unknown string value — treat as require
        ctx = ssl.create_default_context()
        config['ssl'] = ctx

    return config
