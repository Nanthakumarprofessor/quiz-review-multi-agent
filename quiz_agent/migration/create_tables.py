"""
Migration - Create client database tables
"""
from sqlalchemy import create_engine, inspect
from repositories.schemas.schema import Base
from settings import settings
from utils.logger import logger


class Migration:
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        self.inspector = inspect(self.engine)

    def create_tables(self):
        """Create all required tables"""
        logger.info("=" * 60)
        logger.info("CREATING CLIENT DATABASE TABLES")
        logger.info("=" * 60)

        try:
            Base.metadata.create_all(bind=self.engine)
            tables = self.inspector.get_table_names()
            logger.info("TABLES IN DATABASE:")
            for table in tables:
                logger.info(f"   • {table}")
        except Exception as e:
            logger.error(f"Table creation failed: {str(e)}")
            raise
