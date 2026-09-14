"""python restore_model_library.py --owner-id <existing instructor/admin ID>"""
import argparse
import json

from app.core.database import SessionLocal
import app.models  # register relationships before querying users
from app.models.user import User
from app.services.model_library_service import install_library


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner-id', required=True, type=int)
    args = parser.parse_args()
    with SessionLocal() as db:
        owner = db.get(User, args.owner_id)
        if owner is None:
            parser.error('Owner does not exist in the configured database.')
        print(json.dumps({'models': install_library(db, owner)}, indent=2))


if __name__ == '__main__':
    main()
