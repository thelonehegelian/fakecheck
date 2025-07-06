import os
import getpass
import logging
import re
import sys
import json
from fastapi import FastAPI

from langchain_anthropic import ChatAnthropic
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
from fastapi import FastAPI

from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from exa_py import Exa
from typing import List, Optional, Dict, Any
from datetime import datetime
from anthropic import Anthropic

load_dotenv()


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))


app = FastAPI()


# Add CORS middleware to your FastAPI app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your actual frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

anthropic_api_key = os.environ["ANTHROPIC_API_KEY"]
exa_api_key = os.environ["EXA_API_KEY"]
exa = Exa(api_key=exa_api_key)


# Get model from env or use a default valid model
model_name = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")

llm_anthropic = ChatAnthropic(model=model_name, api_key=anthropic_api_key)

default_base_prompt = """ You are a Fake New Detector. USING THE NEWS and the CONTEXT provided
 1. Rate the claim on a fake news meter, from 1-5
2. Explain why it is likely to be Fake. Give Statistics and Facts if available
3. Explain why it is possible that it might be true. Give Statistics and Facts if available
 4. Make suggestion for the steps a user should take to further research these claims. Identify specific things they should look for, don't give generic advice. List them from easiest to do to more complex tasks and approximate the time for each task
 YOU MUST MAINTAIN AN IMPARTIAL AND FAIR TONE.
 """

test_news = """Democrats are trying to pass a bill that:
 1 Provides a pathway to citizenship for
 more than 15 MILLION illegal aliens -
 including aliens who were previously
 deported during the Trump Admin.
15 17 423 1.1K Ill 38K L 
Chad Wol @ChadFWol - Aug 20 **•
2. Requires taxpayers to pay for
previously deported illegal aliens to be
brought back to the U.S.
@ 18. ［し405 1K ill 37K ①
Chad Wol @ChadFWol - Aug 20)
2. Excludes the ability to remove aliens
 with felony records."""


base_prompt = os.environ.get("BASE_PROMPT", default_base_prompt)
custom_prompt = PromptTemplate(
    template=(f"{base_prompt}\n\n" "News: {news}\n\n Context: {context}\n\n" "Answer:"),
    input_variables=["news", "context"],
)


def test_news():
    response = llm_anthropic.invoke(custom_prompt.format(news=test_news))
    print(response.content)


class News(BaseModel):
    news: str


class Result(BaseModel):
    score: float
    title: str
    id: HttpUrl
    url: HttpUrl
    publishedDate: datetime
    author: Optional[str]
    text: str
    summary: str
    image: Optional[HttpUrl]
    favicon: Optional[HttpUrl]


class ExaResponseModel(BaseModel):
    requestId: str
    autopromptString: str
    resolvedSearchType: str
    results: List[Result]


def extract_exa_text(sources: List[Result]):
    return "\n".join([source.text + "\n" + str(source.url) for source in sources])


def extract_exa_sources(sources: List[Result]):
    return "\n".join([str(source.url) for source in sources])


# Define the schema for the fact-check response
article_schema = {
    "type": "object",
    "properties": {
        "fake_news_rating": {
            "type": "integer",
            "description": "Rating from 1-5 where 5 is definitely fake",
            "minimum": 1,
            "maximum": 5,
        },
        "fake_news_explanation": {
            "type": "string",
            "description": "Explanation of why the news might be fake, including statistics and facts",
        },
        "true_news_explanation": {
            "type": "string",
            "description": "Explanation of why the news might be true, including statistics and facts",
        },
        "verification_steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "step": {
                        "type": "string",
                        "description": "Description of the verification step",
                    },
                    "estimated_time": {
                        "type": "string",
                        "description": "Estimated time to complete this step",
                    },
                    "complexity": {
                        "type": "string",
                        "enum": ["easy", "medium", "complex"],
                        "description": "Complexity level of the step",
                    },
                },
                "required": ["step", "estimated_time", "complexity"],
            },
        },
    },
    "required": [
        "fake_news_rating",
        "fake_news_explanation",
        "true_news_explanation",
        "verification_steps",
    ],
}

# Initialize Anthropic client
client = Anthropic(api_key=anthropic_api_key)

# Update the prompt to work with tool calling
system_prompt = """You are a Fake News Detector. Analyze the provided news and context to determine its authenticity.
Maintain an impartial and fair tone throughout your analysis. Do not reflect on the quality of the returned search results in your response."""


@app.post("/check-fake")
async def check_fake(news: News):
    try:
        logging.info("Retrieving news from EXA")
        exa_results: ExaResponseModel = exa.search_and_contents(
            news.news,
            type="auto",
            summary=True,
            text=True,
            num_results=3,
            category="news",
            exclude_domains=["https://x.com/", "https://twitter.com/"],
        )

        exa_text = extract_exa_text(exa_results.results)
        query_results = exa_text + "\n\n" + news.news
        sources = extract_exa_sources(exa_results.results)

        logging.info(f"Sending request to Claude using model: {model_name}")

        # Define the tool
        tools = [
            {
                "name": "format_article",
                "description": "Structure news fact-check analysis with ratings, explanations, and verification steps",
                "input_schema": article_schema,
            }
        ]

        # Use Anthropic client with tool calling
        response = client.messages.create(
            model=model_name,
            max_tokens=4000,
            tools=tools,
            tool_choice={"type": "tool", "name": "format_article"},
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"News to analyze: {news.news}\n\nContext from reliable sources: {exa_text}",
                },
            ],
        )

        # Log the entire response for debugging
        logging.info(f"Response from Claude: {response}")

        # Extract the tool use response
        tool_response = response.content[0].input

        # Return the structured JSON response
        return JSONResponse(content=tool_response, media_type="application/json")

    except Exception as e:
        logging.error(f"Error in check-fake endpoint: {str(e)}")
        import traceback

        logging.error(traceback.format_exc())
        return JSONResponse(
            content={"error": str(e)},
            status_code=500,
        )
