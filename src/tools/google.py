import json
from typing import Optional, Type

from langchain import GoogleSerperAPIWrapper
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from src.tools import NOT_FOUND
from src.utils import cached


class GoogleArgumentsSchema(BaseModel):
    query : str = Field(description="query to search on google, apply SEO techniques to get the best results")

class SerpAPISearch(BaseTool):
    name = "google"
    description = "useful for fact-checking or when you need to find information on events. you should use targeted questions"
    args_schema: Type[GoogleArgumentsSchema] = GoogleArgumentsSchema

    tool : Optional[GoogleSerperAPIWrapper] = None
    top_k : int = 0
    def __init__(self, top_k=3, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tool = GoogleSerperAPIWrapper(gl='es', hl='es', type="search")
        self.top_k = top_k

    @cached(key_func_name="google")
    def _run(self, query: str) -> str:
        """Run query through SerpAPI and parse result."""
        response = self._process_response(self.tool.results(query))
        return json.dumps(response)

    def _process_response(self, res: dict) -> list:
        """Process response from SerpAPI."""
        # self._res = res
        if "error" in res.keys():
            raise ValueError(f"Got error from SerpAPI: {res['error']}")
        if ("organic" in res.keys()):
            toret = [{'title': d['title'], 
                      'url': d['link'], 
                      'description': d['snippet']} for d in res["organic"][:self.top_k]]
        else:
            toret = [{"description": NOT_FOUND}]
        return toret

    async def _arun(self, query: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("GoogleSearchRun does not support async")