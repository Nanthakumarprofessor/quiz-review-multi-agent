# tools.py
import json
import re
from typing import Annotated

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools.base import InjectedToolCallId
from langgraph.types import Command

from agent.system_prompt import QUIZ_AGENT_PROMPT, REVIEW_AGENT_PROMPT
from utils.logger import logger


def make_quiz_agent_tool(llm):
    @tool
    def quiz_agent(
        topic: str,
        difficulty: str,
        questions_count: int,
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        """Generate quiz questions for the given topic, difficulty, and count."""
        prompt = QUIZ_AGENT_PROMPT.format(
            topic=topic,
            difficulty=difficulty,
            questions_count=questions_count,
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = response.content.strip()

        try:
            questions = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            questions = json.loads(match.group()) if match else []

        logger.info(f"Quiz agent generated {len(questions)} questions")

        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=json.dumps(questions),
                        tool_call_id=tool_call_id,
                    )
                ],
            }
        )

    return quiz_agent


def make_review_agent_tool(llm):
    @tool
    def review_agent(
        questions_and_answers: str,
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        """Review and evaluate user answers against the quiz questions."""
        prompt = f"{REVIEW_AGENT_PROMPT}\n\nQuestions and Answers:\n{questions_and_answers}"
        response = llm.invoke([HumanMessage(content=prompt)])
        feedback = response.content.strip()

        logger.info("Review agent completed evaluation")

        return Command(
            update={
                "messages": [
                    ToolMessage(
                        content=feedback,
                        tool_call_id=tool_call_id,
                    )
                ],
            }
        )

    return review_agent
