import os

# from duckduckgo_search import DDGS
import getpass
import logging
import re
import sys
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
from typing import List, Optional
from datetime import datetime

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


# TODO get model from env
llm_anthropic = ChatAnthropic(
    model="claude-3-5-sonnet-latest", api_key=anthropic_api_key
)

default_base_prompt = """ You are a Fake New Detector. USING THE NEWS and the CONTEXT provided
 1. Rate the claim on a fake news meter, from 1-5
 2. Explain why it is likely to be Fake
 3. Explain why it is possible that it might be true
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
    return "\n".join([source.text for source in sources])


def extract_exa_sources(sources: List[Result]):
    return "\n".join([source.url for source in sources])


@app.post("/check-fake")
def check_fake(news: News):
    print("Retrieving news from EXA")
    exa_results: ExaResponseModel = exa.search_and_contents(
        news.news,
        type="auto",
        summary=True,
        text=True,
        num_results=5,
        category="news",
        exclude_domains=["https://x.com/", "https://twitter.com/"],
    )
    exa_text = extract_exa_text(exa_results.results)
    query_results = exa_text + news.news
    sources = extract_exa_sources(exa_results.results)
    llm_response = llm_anthropic.invoke(
        custom_prompt.format(news=query_results, context=exa_text)
    )
    print(sources)
    test_response = "Testing"
    # return JSONResponse(content=test_response, media_type="text/html")
    return JSONResponse(content=llm_response.content, media_type="text/html")


# This is the web search
# TODO get model from env
# def summariser(search_term, model="claude-3-haiku-20240307"):
#     model = model
#     llm_anthropic = Anthropic(model=model)
#     api_key = os.getenv("ANTHROPIC_API_KEY")
#     if not api_key:
#         raise EnvironmentError("ANTHROPIC_API_KEY not set in environment variables.")

#     # Search for URLs using the provided search term using DuckDuckGo
#     results = DDGS().text(search_term, max_results=5)
#     if not results:
#         return "No search results found."

#     url = results[0]["href"]
#     test = "https://www.9news.com/article/news/politics/vice-president-kamala-harris-plan-immigration-elected-president/73-9d3d39ed-f7e9-4071-b6ae-b752b640fc1f"
#     # Load data from the identified URL
#     documents = SimpleWebPageReader(html_to_text=True).load_data([test])

#     system_command = "You are a summariser. Write a brief summary in a single paragraph"
#     # Step: Prepare the summarizer chat message
#     summariser_message = [
#         ChatMessage(
#             role="system",
#             content=system_command,
#         ),
#         ChatMessage(role="user", content=str(documents)),
#     ]

#     # Step: Get the summary from the Anthropic model
#     resp = llm_anthropic.chat(summariser_message)

#     # Return the summary response
#     return resp


# search_term = "vaccine robert f kennedy jr"
# summary = summariser(search_term)
# print(summary)

# reader = SimpleWebPageReader(url=page)

# print(reader)

# 1. parse the webpages/news pages
# 2. do an in memory rag
# 3. answer the query


# # claude-3-sonnet-20240229

# fake_news = """
# Democrats are trying to pass a bill that:
# 1 Provides a pathway to citizenship for
# more than 15 MILLION illegal aliens -
# including aliens who were previously
# deported during the Trump Admin.
# 15 17 423 1.1K Ill 38K L
# Chad Wol @ChadFWol - Aug 20 **•
# 2. Requires taxpayers to pay for
# previously deported illegal aliens to be
# brought back to the U.S.
# @ 18. ［し405 1K ill 37K ①
# Chad Wol @ChadFWol - Aug 20)
# 2. Excludes the ability to remove aliens
# with felony records.
# """
# messages = [
#     ChatMessage(
#         role="system",
#         content=""" You are a Fake New Detector.
# 1. Rate this claim on a fake news meter, from 1-5
# 2. Explain why it is likely to be Fake
# 3. Explain why it is possible that it might be true
# 4. Make suggestion for the steps a user should take to further research these claims. Identify specific things they should look for, don't give generic advice. List them from easiest to do to more complex tasks and approximate the time for each task
# YOU MUST MAINTAIN A IMPARTIAL AND FAIR TONE.
# """,
#     ),
#     ChatMessage(role="user", content=fake_news),
# ]
# resp = Anthropic(model=model).stream_chat(messages)

# for r in resp:
#     print(r.delta, end="")


# def query_using_indexer(url, query, llm):
#     # Step: Load data from the URL
#     documents = SimpleWebPageReader(html_to_text=True).load_data([url])

#     # Step: Create a document summary index
#     summary_index = DocumentSummaryIndex.from_documents(documents, llm=llm)

#     # Step: Initialize the query engine
#     query_engine = summary_index.as_query_engine()

#     # Step: Execute the query
#     response = query_engine.query(query)

#     # Return the response
#     return response
