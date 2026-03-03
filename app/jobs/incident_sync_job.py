import logging

from app.database.session import SessionLocal
from app.services.sync_service import build_servicenow_client, run_incident_sync
from app.utils.config import get_settings
from app.utils.logging import setup_logging


logger = logging.getLogger(__name__)


def run() -> dict[str, int | str | bool]:
    settings = get_settings()
    setup_logging(settings.log_level)

    client = build_servicenow_client(settings)
    db = SessionLocal()
    try:
        return run_incident_sync(db=db, client=client)
    finally:
        db.close()


if __name__ == "__main__":
    summary = run()
    logger.info("Cron incident sync completed: %s", summary)
