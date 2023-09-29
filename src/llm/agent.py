from __future__ import annotations
import hashlib
import json

from typing import Tuple, List, Optional, Any, Dict

from langchain.chains.llm import LLMChain
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import (
    AIMessage,
    BaseMessage,
    Document,
    HumanMessage,
    SystemMessage,
)
from langchain.tools.base import BaseTool

from src.llm.models import Action, iCalendar, Event
from src.utils import try_loads, retrieve_by_key, save

from loguru import logger

class img2calendar:
    """Agent class for interacting with EventGPT."""

    def __init__(
        self,
        chain: LLMChain,
        chain_icalendar: LLMChain,
        tools: List[BaseTool],
        callbacks: Optional[List[BaseCallbackHandler]] = None
    ):
        self.full_message_history: List[BaseMessage] = []
        self.chain = chain
        self.chain_icalendar = chain_icalendar
        self.tools = tools
        self.callbacks = callbacks or []

    @property
    def tools_template(self) -> str:
        return '\n'.join(self._generate_tools(self.tools))

    @property
    def memory_template(self) -> str:
        return json.dumps(self.full_message_history, indent=2)

    @property
    def tools_dict(self) -> dict:
        return {tool.name: tool for tool in self.tools}

    @classmethod
    def from_chain_and_tools(
        cls,
        template: str,
        tools: List[BaseTool],
        chain: LLMChain,
        chain_icalendar: LLMChain,
        callbacks: Optional[List[BaseCallbackHandler]] = None,
    ) -> img2calendar:
        if callbacks and len(callbacks) > 0:
            for tool in tools:
                tool.callbacks = callbacks
        return cls(
            chain,
            chain_icalendar,
            tools,
            callbacks=callbacks
        )

    def initialize(self, image: str) -> None:
        # bootstrap memory with the loading message
        self.full_message_history = [{"id": 0, "name": "load_image", "result": "Image is loaded. Please state your next question?"}]
        ocr: BaseTool = self.tools_dict.get("ocr")
        if ocr  is not None:
            self._callback_handler("on_step", step=1)
            ocr_content = ocr.run({'url': image})
            self.full_message_history.append({"id": 1, "name": "ocr", "result": ocr_content})
        self.total_tokens_ = 0

    def _check_agent_cache(self, ocr_content: str) -> Optional[Tuple[str, Event]]:
        key = hashlib.sha1(ocr_content.encode()).hexdigest()
        result = retrieve_by_key(key)
        if result:
            result = json.loads(result)
            return result[0], Event.parse_obj(result[1])
        return None
    
    def _save_agent_cache(self, ocr_content: str, icalendar: str, event: str) -> None:
        logger.info ("Saving cache for agent ...")
        key = hashlib.sha1(ocr_content.encode()).hexdigest()
        save(key, "agent-"+ocr_content, [icalendar, event])

    def run(self, image: str, max_steps = 10, force = False) -> Tuple[Optional[str], Optional[str]]:
        self._callback_handler("on_agent_start", image=image)
        self.initialize(image)
        if not force:
            cached_result = self._check_agent_cache(self.full_message_history[1]["result"])
            if cached_result:
                logger.info ("Using cached value for agent")
                self._callback_handler("on_agent_end", calendar=cached_result[0])
                return cached_result
        assistant_reply: Optional[Action] = None
        for step in range(2, max_steps):
            self._callback_handler("on_step", step=step)
            assistant_reply = self.chain.run(memory = self.memory_template, commands = self.tools_template, callbacks=self.callbacks)
            self._callback_handler("on_step", step=step, assistant_reply=assistant_reply)
            if assistant_reply.command is None:
                logger.info ("I'm done!")
                break
            try:
                tool = list(filter(lambda x: x.name == assistant_reply.command.name, self.tools))[0]
            except AttributeError as ex:
                logger.error (ex)
                continue

            observation = tool.run(dict(zip(tool.args, assistant_reply.command.args)))
            self.full_message_history.append({"id": len(self.full_message_history), 
                                        "name": assistant_reply.command.name, 
                                        "args": assistant_reply.command.args, 
                                        "result": try_loads(observation, True)})

        if assistant_reply.iCalendar:
            self._callback_handler("on_agent_end", calendar=assistant_reply.iCalendar)
            self._save_agent_cache(self.full_message_history[1]["result"], assistant_reply.iCalendar, assistant_reply.event)
            return assistant_reply.iCalendar, assistant_reply.event
        else:
            # last try, now using icalendar chain
            self._callback_handler("on_step", step=step)
            calendar_reply:iCalendar = self.chain_icalendar.run(memory = self.memory_template, callbacks=self.callbacks)
            if calendar_reply.iCalendar:
                self._callback_handler("on_agent_end", calendar=calendar_reply.iCalendar)
                self._save_agent_cache(self.full_message_history[1]["result"], calendar_reply.iCalendar, assistant_reply.event)
                return calendar_reply.iCalendar, assistant_reply.event
            else:
                self._callback_handler("on_agent_end", calendar=None)
                logger.error ("No iCalendar found")
                return None, assistant_reply.event

    def _generate_tools(self, tools: List[BaseTool]) -> List[str]:
        command_strings = [
            f"{i + 1}. {self._generate_command_string(item)}"
            for i, item in enumerate(tools)
        ]
        return command_strings

    def _generate_command_string(self, tool: BaseTool) -> str:
        return f'{json.dumps([tool.name] + list(tool.args.keys())).replace("[","").replace("]","")} : {tool.description}, '

    def _callback_handler(self, event_name, *args, **kwargs: Any) -> Any:
        """Run a callback handler."""
        for callback in self.callbacks:
            try:
                getattr(callback, event_name)(*args, **kwargs)
            except NotImplementedError as e:
                logger.warning(f"Callback {callback} does not implement {event_name}")


def make_agent(callbacks: Optional[List[BaseCallbackHandler]] = None):
    from langchain.chat_models import AzureChatOpenAI, ChatOpenAI
    from langchain import PromptTemplate
    from langchain.output_parsers.openai_functions import PydanticOutputFunctionsParser
    from langchain.chains.question_answering import load_qa_chain
    from langchain.chains.openai_functions import (
        create_openai_fn_chain,
        create_structured_output_chain,
    )

    from src.tools.google import SerpAPISearch
    from src.tools.gmaps import SerpAPILocation
    from src.tools.webpageqa import WebpageQA
    from src.tools.ocr import OcrTool

    from src.llm.prompt import PROMPT, ICALENDAR
    from src.llm.models import Action, iCalendar


    llm = AzureChatOpenAI(deployment_name="agent", temperature=0, verbose=True) # type: ignore
    llm_chat = AzureChatOpenAI(deployment_name="chat", temperature=0, verbose=True) # type: ignore

    webpageqa = WebpageQA(qa_chain=load_qa_chain(llm_chat, chain_type="stuff"))
    google = SerpAPISearch()
    gmaps = SerpAPILocation()
    ocr = OcrTool()

    tools = [ocr, google, gmaps, webpageqa]

    for tool in tools:
        tool.callbacks = None
    chain = create_openai_fn_chain([Action], llm, prompt=PromptTemplate(template=PROMPT, input_variables=['memory', 'commands']),
                                output_parser=PydanticOutputFunctionsParser(pydantic_schema=Action))
    chain_icalendar = create_structured_output_chain(iCalendar, llm, PromptTemplate(template=ICALENDAR, input_variables=['memory']))

    agent = img2calendar.from_chain_and_tools(PROMPT, tools, chain, chain_icalendar, callbacks=callbacks)

    return agent
