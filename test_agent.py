"""
Direct test script for MainAgent execution
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "quiz_agent"))

from agent.agent import MainAgent
from utils.logger import logger


async def main():
    logger.info("Initializing MainAgent for direct test...")
    agent = await MainAgent.create()

    user_id = 99
    topic = "Python Basics"
    difficulty = "easy"
    questions_count = 2
    answers = ["Guido van Rossum", "A programming language"]

    logger.info(f"Running quiz session for user {user_id}...")
    response = await agent.run_quiz_session(
        user_id=user_id,
        topic=topic,
        difficulty=difficulty,
        questions_count=questions_count,
        answers=answers,
    )

    print("\n" + "=" * 50)
    print("TEST EXECUTION COMPLETED")
    print("=" * 50)
    print(f"User ID: {response.user_id}")
    print(f"Response Feedback:\n{response.response}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
