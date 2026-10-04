# routes/chat_router.py
import uuid
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from service.chat_service import ChatService
from models.chat_models import ChatRequestDTO
from utils.logger import logger
from repositories.database.session import SessionLocal
from repositories.client_error_repository import ClientErrorRepository

router = APIRouter()
chat_service = ChatService()


@router.post("/chat")
async def chat(request: ChatRequestDTO):
    db = None
    try:
        logger.info(f"Quiz request received — user {request.user_id}: topic='{request.query}', difficulty='{request.difficulty}', count={request.questions_count}")
        response = await chat_service.process_message(request)
        return {"response": response}

    except Exception as e:
        logger.error(f"Chat error: {str(e)}")

        try:
            db = SessionLocal()
            error_repo = ClientErrorRepository(db)
            error_repo.log_error(
                request_id=str(uuid.uuid4()),
                function_name="chat",
                file_name="chat_router.py",
                error=e,
            )
        except Exception as db_error:
            logger.error(f"Failed to log error to database: {db_error}")
        finally:
            if db:
                db.close()

        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(e)},
        )
