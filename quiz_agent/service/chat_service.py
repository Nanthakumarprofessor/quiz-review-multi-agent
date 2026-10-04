# chat_service.py
"""
Chat Service
"""
import uuid
from agent.agent import MainAgent
from models.chat_models import ChatRequestDTO, AgentResponse
from utils.logger import logger
from repositories.database.session import SessionLocal
from repositories.client_error_repository import ClientErrorRepository


class ChatService:
    def __init__(self):
        self.agent = None
        self.initialized = False

    async def ensure_agent(self):
        if not self.initialized:
            try:
                self.agent = await MainAgent.create()
                self.initialized = True
                logger.info("MainAgent initialized successfully in ChatService")
            except Exception as e:
                logger.error(f"Failed to initialize MainAgent: {e}")
                raise

    async def process_message(self, request: ChatRequestDTO) -> AgentResponse:
        db = None
        try:
            await self.ensure_agent()
            response = await self.agent.run_quiz_session(
                user_id=request.user_id,
                topic=request.query,
                difficulty=request.difficulty,
                questions_count=request.questions_count,
                answers=request.answers,
            )
            return response

        except Exception as e:
            logger.error(f"Chat service error: {e}")
            try:
                db = SessionLocal()
                error_repo = ClientErrorRepository(db)
                error_repo.log_error(
                    request_id=str(uuid.uuid4()),
                    function_name="process_message",
                    file_name="chat_service.py",
                    error=e,
                )
            except Exception as db_err:
                logger.error(f"Error logging failed in chat service: {db_err}")
            finally:
                if db:
                    db.close()
            raise