"""
Client Error Repository
"""
import traceback
from repositories.database.session import SessionLocal
from repositories.schemas.schema import ErrorLog
from utils.logger import logger


class ClientErrorRepository:
    def __init__(self, db_session=None):
        self.db = db_session or SessionLocal()

    def close(self):
        if self.db:
            self.db.close()

    def log_error(self, request_id: str, function_name: str, file_name: str, error: Exception, error_message: str = None):
        """Log error to database"""
        try:
            error_name = error.__class__.__name__ if error else "Unknown"
            error_msg = str(error) if error else error_message

            # Add traceback if available
            tb = traceback.format_exc()
            if tb and tb != "None\n":
                error_msg = f"{error_msg}\n{tb}"

            error_log = ErrorLog(
                request_id=request_id,
                function_name=function_name,
                file_name=file_name,
                error_name=error_name,
                error_message=error_msg[:1000] if error_msg else None,
                created_by="client",
            )

            self.db.add(error_log)
            self.db.commit()
            logger.info(f"Error logged: {error_name} in {function_name}")

        except Exception as e:
            logger.error(f"ClientErrorRepository Error: {str(e)}")
            self.db.rollback()
        finally:
            self.close()