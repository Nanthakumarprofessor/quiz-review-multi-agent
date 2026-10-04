# agent.py
import json
from typing import Literal, Optional, List
from typing_extensions import NotRequired

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import MessagesState
from langchain_core.messages import HumanMessage, SystemMessage

from settings import settings
from agent.system_prompt import QUIZ_STEP_PROMPT, REVIEW_STEP_PROMPT
from agent.tools import make_quiz_agent_tool, make_review_agent_tool
from models.chat_models import AgentResponse
from utils.logger import logger


# ─────────────────────────────────────────────
# Step 1: State — extends MessagesState with quiz workflow fields
# ─────────────────────────────────────────────

class QuizState(MessagesState):
    remaining_steps: NotRequired[int]
    current_step:    NotRequired[Literal["quiz_step", "review_step"]]
    topic:           NotRequired[str]
    difficulty:      NotRequired[str]
    questions_count: NotRequired[int]
    qa_pairs:        NotRequired[str]


# ─────────────────────────────────────────────
# Step 2: STEP_CONFIG — prompt template + allowed tools per step
# ─────────────────────────────────────────────

def build_step_config(quiz_tool, review_tool: object) -> dict:
    return {
        "quiz_step": {
            "prompt":   QUIZ_STEP_PROMPT,
            "tools":    [quiz_tool],
            "requires": ["topic", "difficulty", "questions_count"],
        },
        "review_step": {
            "prompt":   REVIEW_STEP_PROMPT,
            "tools":    [review_tool],
            "requires": ["qa_pairs"],
        },
    }


# ─────────────────────────────────────────────
# Step 3: Dynamic prompt callable
# ─────────────────────────────────────────────

def build_prompt_fn(step_config: dict):
    def prompt_fn(state: dict) -> list:
        current_step = state.get("current_step", "quiz_step")
        cfg = step_config[current_step]

        for key in cfg["requires"]:
            if not state.get(key):
                raise ValueError(f"'{key}' must be set before step '{current_step}'")

        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None

        # Once a tool has returned its ToolMessage, instruct the agent to stop calling tools
        if last_message and last_message.__class__.__name__ == "ToolMessage":
            system_prompt = (
                "The tool execution is complete and the result is available above. "
                "Do NOT call any more tools. Summarize or present the final output to the user."
            )
        else:
            system_prompt = cfg["prompt"].format(**state)

        return [SystemMessage(content=system_prompt)] + messages

    return prompt_fn


# ─────────────────────────────────────────────
# Step 4: MainAgent
# ─────────────────────────────────────────────

class MainAgent:
    def __init__(self, agent, structured_llm):
        self.agent = agent
        self.structured_llm = structured_llm

    @classmethod
    async def create(cls):
        provider = settings.LLM_PROVIDER.lower()
        logger.info(f"Initializing MainAgent with LLM provider: {provider}")

        if provider == "bedrock":
            import boto3
            from langchain_aws import ChatBedrock

            bedrock_runtime = boto3.client(
                service_name="bedrock-runtime",
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )

            llm = ChatBedrock(
                client=bedrock_runtime,
                model_id=settings.BEDROCK_MODEL_ID,
                provider="amazon",
                streaming=False,
                model_kwargs={
                    "temperature": settings.TEMPERATURE,
                    "max_tokens":  settings.MAX_TOKENS,
                },
            )
        else:
            from langchain_ollama import ChatOllama
            logger.info(f"Connecting to Ollama at {settings.OLLAMA_BASE_URL} with model: {settings.OLLAMA_MODEL}")
            llm = ChatOllama(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.OLLAMA_MODEL,
                temperature=settings.TEMPERATURE,
            )

        structured_llm = llm.with_structured_output(AgentResponse)

        quiz_tool   = make_quiz_agent_tool(llm)
        review_tool = make_review_agent_tool(llm)

        step_config = build_step_config(quiz_tool, review_tool)
        prompt_fn   = build_prompt_fn(step_config)

        agent = create_react_agent(
            model=llm,
            tools=[quiz_tool, review_tool],
            prompt=prompt_fn,
            state_schema=QuizState,
            checkpointer=InMemorySaver(),
        )

        logger.info("MainAgent initialized successfully with dynamic step-config prompt")
        return cls(agent, structured_llm)

    async def run_quiz_session(
        self,
        user_id: int,
        topic: str,
        difficulty: str,
        questions_count: int,
        answers: Optional[List[str]] = None,
    ) -> AgentResponse:
        try:
            config = {"configurable": {"thread_id": f"quiz_{user_id}"}}

            # Phase 1 — Quiz generation
            logger.info(f"Phase 1: Generating quiz for user {user_id}...")
            state = await self.agent.ainvoke(
                {
                    "messages":        [HumanMessage(content="Start the quiz.")],
                    "current_step":    "quiz_step",
                    "topic":           topic,
                    "difficulty":      difficulty,
                    "questions_count": questions_count,
                },
                config=config,
            )

            questions = self._extract_questions(state["messages"])
            if not questions:
                raise ValueError("Quiz agent did not return any questions")

            logger.info(f"Phase 1 complete: Collected {len(questions)} questions")

            # Phase 2 — Collect answers
            user_answers = []
            if answers and len(answers) > 0:
                logger.info("Phase 2: Using answers supplied in request")
                for i, q in enumerate(questions):
                    ans = answers[i] if i < len(answers) else ""
                    user_answers.append(ans)
            else:
                logger.info("Phase 2: Collecting answers interactively from terminal")
                for i, q in enumerate(questions, 1):
                    print(f"\nQ{i}: {q.get('question', '')}")
                    answer = input("Your answer: ").strip()
                    user_answers.append(answer)

            qa_pairs = "\n".join(
                f"Q{i}: {q.get('question', '')}\nA{i}: {a}"
                for i, (q, a) in enumerate(zip(questions, user_answers), 1)
            )

            # Phase 3 — Review answers
            logger.info(f"Phase 3: Reviewing answers for user {user_id}...")
            final_state = await self.agent.ainvoke(
                {
                    "messages":     [HumanMessage(content=f"Please review these questions and answers:\n{qa_pairs}")],
                    "current_step": "review_step",
                    "qa_pairs":     qa_pairs,
                },
                config=config,
            )

            feedback = self._extract_feedback(final_state["messages"])
            logger.info("Phase 3 complete: Review received")

            # Phase 4 — Format into structured AgentResponse
            logger.info(f"Phase 4: Structuring output for user {user_id}...")
            # The review feedback from Phase 3 is already the complete per-question evaluation
            structured = AgentResponse(user_id=user_id, response=feedback)
            logger.info(f"Quiz session successfully completed for user {user_id}")
            return structured

        except Exception as e:
            logger.error(f"Agent error in run_quiz_session: {e}")
            raise

    def _extract_questions(self, messages: list) -> list:
        for msg in reversed(messages):
            if msg.__class__.__name__ == "ToolMessage":
                try:
                    data = json.loads(msg.content)
                    if isinstance(data, list) and data:
                        return data
                except (json.JSONDecodeError, TypeError):
                    continue
        return []

    def _extract_feedback(self, messages: list) -> str:
        # Check ToolMessages for the review evaluation
        for msg in reversed(messages):
            if msg.__class__.__name__ == "ToolMessage" and msg.content:
                return msg.content
        if messages and messages[-1].content:
            return messages[-1].content
        return "Quiz evaluation complete."
