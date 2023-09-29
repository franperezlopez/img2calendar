import json
from typing import Optional, Type

from langchain import GoogleSerperAPIWrapper
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from src.tools import NOT_FOUND
from src.tools.map import OpenStreetAPI
from src.utils import cached


class DidYouMeanError(ValueError):
    def __init__(self, whereis: str, *args: object) -> None:
        super().__init__(*args)
        self.whereis = whereis

class GmapsArgumentsSchema(BaseModel):
    location : str = Field(description="location to search on google maps")

class SerpAPILocation(BaseTool):
    name = "gmaps"
    description = "useful for fact-checking on event locations"
    args_schema: Type[GmapsArgumentsSchema] = GmapsArgumentsSchema

    prefix : Optional[str] = None
    tool : Optional[GoogleSerperAPIWrapper] = None
    geocoder : Optional[OpenStreetAPI] = None
    def __init__(self, prefix: str = "where is", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prefix = prefix
        self.tool = GoogleSerperAPIWrapper(gl='es', hl='es', type="search")
        self.geocoder = OpenStreetAPI()

    @cached(key_func_name="whereis")
    def _run(self, location: str) -> str:
        """Run query through SerpAPI and parse result."""
        try:
            toret = self._process_response(self.tool.results(f"{self.prefix} {location}"))
        except DidYouMeanError as ex:
            toret = self._process_response(self.tool.results(ex.whereis))
        if toret.get("address") is None:
            toret = self._process_response_if_not_found(location)
        return json.dumps(toret)

    def _process_response(self, res: dict) -> dict:
        """Process response from SerpAPI."""

        if "error" in res.keys():
            raise ValueError(f"Got error from SerpAPI: {res['error']}")
        toret = {}
        if "searchInformation" in res.keys():
            if "didYouMean" in res["searchInformation"]:
                raise DidYouMeanError(whereis=res['searchInformation']['didYouMean'])
        if ("knowledgeGraph" in res.keys()):
            toret["address"] = res["knowledgeGraph"]
        if ("answerBox" in res.keys()):
            toret["address"] = res["answerBox"].get("answer")
        return toret

    def _process_response_if_not_found(self, query):
        response = self.geocoder.whereis(query)
        if response != NOT_FOUND:
            response = [{"title": query,
                         "description": response}]
        return response

    async def _arun(self, query: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("Google Search does not support async")