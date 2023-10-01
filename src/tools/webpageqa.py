import json
from typing import Optional, Type

from langchain.chains.qa_with_sources.loading import BaseCombineDocumentsChain
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field

from src.tools.playwright import Playwright
from src.utils import DEFAULT_CACHE, cached, try_loads

# Code based on https://python.langchain.com/en/latest/use_cases/autonomous_agents/marathon_times.html

def _get_text_splitter():
    return RecursiveCharacterTextSplitter(
        # Set a really small chunk size, just to show.
        chunk_size = 3000,
        chunk_overlap  = 30,
        length_function = len,
    ).from_tiktoken_encoder()


class WebpageQA(StructuredTool):
    class RunArgsSchema(BaseModel):
        url: str = Field(description="url to search on google maps")
        query_context: str = Field(description="concise summary including all event information")
        query: str = Field(description=" question to ask to the webpage; you can ask many event attributes at once, but you need to provide a concise summary of the event information")

    name = "webpageqa"
    description = "web page question answering, useful when you need extract and/or fact-check event data"
    text_splitter: RecursiveCharacterTextSplitter = Field(default_factory=_get_text_splitter)
    tool = Optional[Playwright]
    qa_chain: Optional[BaseCombineDocumentsChain]
    args_schema: Type[RunArgsSchema] = RunArgsSchema

    def __init__(self, qa_chain: BaseCombineDocumentsChain, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.qa_chain = qa_chain
        self.tool = Playwright()

    @cached(DEFAULT_CACHE, key_func_name="webpageqa")
    def _run(self, url: str, query_context:str, query: str) -> str:
        """Useful for browsing websites and scraping the text information."""
        playw_result = self.tool.run(url)
        try:
            result = try_loads(playw_result.strip("'").strip('"')) or try_loads(try_loads(playw_result))
        except Exception as ex:
            print (f"error inspecting {url} with query {query} and query_context {query_context}")
            return "Error loading page"
        if result["title"] == "ERROR" and result["body"] == "":
            return "Error loading page"
        docs = [Document(page_content=result["body"], metadata={"source": url, "title": result["title"]} )]
        chunks = self.text_splitter.split_documents(docs)

        return self.qa_chain({"input_documents": chunks, "question": f"{query} \nOnly consider information related to this event: {query_context}"}, return_only_outputs=True)
    
    async def _arun(self, url: str, question: str) -> str:
        raise NotImplementedError
      