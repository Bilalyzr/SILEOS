"""Small compatibility wrapper for the repo's create_all-before-Alembic deploy mode."""

import sqlalchemy as sa


class IdempotentCreateOperations:
    """Skip table/index creation when ``Base.metadata.create_all`` ran first.

    Historical SashaInfinity deployments bootstrap the ORM schema on process
    start and then apply Alembic. Revisions must therefore tolerate their
    target tables and indexes already being present. All destructive and
    alter operations still delegate unchanged.
    """

    def __init__(self, delegate):
        self._delegate = delegate

    def __getattr__(self, name):
        return getattr(self._delegate, name)

    def create_table(self, table_name, *columns, **kwargs):
        inspector = sa.inspect(self._delegate.get_bind())
        if inspector.has_table(table_name):
            return None
        return self._delegate.create_table(table_name, *columns, **kwargs)

    def create_index(self, index_name, table_name, columns, **kwargs):
        inspector = sa.inspect(self._delegate.get_bind())
        if not inspector.has_table(table_name):
            return None
        existing = {row["name"] for row in inspector.get_indexes(table_name)}
        if index_name in existing:
            return None
        return self._delegate.create_index(index_name, table_name, columns, **kwargs)


def idempotent_create_operations(delegate):
    return IdempotentCreateOperations(delegate)
