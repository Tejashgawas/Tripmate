from openai import OpenAI
import os
from app.core.config import settings
from app.core.logger import logger
from fastapi import HTTPException, status
from typing import List, Dict, Any
from openai import OpenAIError

client = OpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url=settings.BASE_URL,
)



def get_ai_completion(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=[
            {"role": "system", "content": "You are an expert travel planner and itinerary creator. Your goal is to design detailed, day-by-day travel plans based on user requests, ensuring the output is always a well-structured JSON array."},
            {"role": "user", "content": prompt},
            ],
            temperature=0.7
        )
    except OpenAIError as e:
        logger.error(f"🔥 LLM backend error: {e}")
        raise HTTPException(status_code=502, detail="AI model is temporarily unavailable.")
    logger.info("✅ LLM connection successful. Response received.")
    
    # print(response.choices[0].message.content)
  
    if not response.choices:
        logger.error("❌ No choices returned from LLM!")
        raise ValueError("LLM did not return any content.")
  
    return response.choices[0].message.content


