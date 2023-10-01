import re
from typing import Tuple, List, Optional, Any, Dict
from uuid import UUID
import streamlit as st
from datetime import datetime as dt
from collections import defaultdict
from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import LLMResult

import logging
from pprint import pformat, pprint
from loguru import logger

from src.llm.models import Action
from src.utils import try_loads

class OutputCallbackHandler(BaseCallbackHandler):
    run_total_tokens: List[int] = []

    def reset(self) -> None:
        """Reset the callback handler."""
        self.run_total_tokens = []

    def on_agent_start(self, **kwargs: Any) -> None:
        """Run when agent starts running."""
        logger.info("AGENT STARTED")
        self.reset()

    def on_agent_end(self, calendar: str, **kwargs: Any) -> None:
        """Run when agent starts running."""
        logger.info("AGENT ENDED")
        logger.info(calendar)


    def on_step(self, step: int, **kwargs: Any) -> None:
        """Run when agent process thoughts."""
        logger.info("STEP")
        self._current_step = step
        if kwargs.get("parsed_assistant_reply"):
            logging.info("\n" + pformat(kwargs["parsed_assistant_reply"].asdict()))

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> Any:
        """Run when LLM starts running."""
        logger.info("LLM STARTED")
        # logger.info(pformat(prompts))
        # print(serialized)

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        """Run when LLM ends running."""
        logger.info("LLM ENDED")
        try:
            function_calling = response.generations[0][0].message.additional_kwargs
            if function_calling:
                logger.info("\n" + pformat(function_calling))
        except:
            pass
        self.run_total_tokens.append(response.llm_output["token_usage"]["total_tokens"])

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> Any:
        """Run when tool starts running."""
        logger.info("TOOL STARTED")
        logger.info({"name": serialized["name"], "input": input_str})

    def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        """Run when tool ends running."""
        logger.info("TOOL ENDED")
        logger.info(output)
    
    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], *, run_id: UUID, parent_run_id: UUID | None = None, tags: List[str] | None = None, **kwargs: Any) -> Any:
        logger.info("CHAIN STARTED")

    def on_chain_end(self, output: Dict[str, Any], *, run_id: UUID, parent_run_id: UUID | None = None, tags: List[str] | None = None, **kwargs: Any) -> Any:
        logger.info("CHAIN ENDED")
        if output.get('full_generation'):
            logger.info("\n" + pformat(output['full_generation'][0].text))
        else:
            logger.info("No text found")


class StreamlitCallbackHandler(BaseCallbackHandler):
    tool_history: Dict[str, Dict[str, str]] = {}
    run_total_tokens: List[int] = []
    run_total_tools: dict[str, List[int]] = defaultdict(list)

    def reset(self) -> None:
        """Reset the callback handler."""
        self.tool_history = {}
        self.run_total_tokens = []

    def set_app(self, steps: int, pb: st.progress, tabs: st.tabs, result: st.container):
        self._steps = steps
        self._current_step = 0
        self._pb = pb
        self._tabs = tabs
        self._result = result
        self._timer: dt = dt.now()

    def on_agent_start(self, **kwargs: Any) -> None:
        """Run when agent starts running."""
        logger.info("AGENT STARTED")
        self.reset()

    def on_agent_end(self, calendar: str, **kwargs: Any) -> None:
        """Run when agent starts running."""
        logger.info("AGENT ENDED")
        # print (kwargs["calendar"])
        self._pb.progress(1., text=f"DONE")
        if calendar:
            # self._result.success("```\n"+calendar+"\n```")
            self._result.text_area("iCalendar", calendar, height=300, disabled=True)
            self._result.download_button('Download iCalendar', calendar, file_name='event.ics', mime='text/calendar')
        self._result.info(f"Total tokens in all steps: {sum(self.run_total_tokens)}")
        self._result.info(f"Total time: {round(sum(sum(self.run_total_tools.values(), [])),2)}s. Total time per tool:")
        self._result.bar_chart({key:sum(value) for key, value in self.run_total_tools.items()})

    def on_step(self, step: int, **kwargs: Any) -> None:
        """Run when agent process thoughts."""
        logger.info("STEP")
        self._current_step = step - 1
        if kwargs.get("assistant_reply"):
            assistant_reply: Action = kwargs["assistant_reply"]
            logger.info("\n" + pformat(assistant_reply.command))
            self._format_thoughts(assistant_reply.thoughts, self._tabs[self._current_step])

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> Any:
        """Run when LLM starts running."""
        logger.info("LLM STARTED")
        self._pb.progress(self._current_step/self._steps, text=f"[{self._current_step+1}] Calling GPT4 ...")
        self._timer = dt.now()

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        """Run when LLM ends running."""
        logger.info("LLM ENDED")
        try:
            function_calling = response.generations[0][0].message.additional_kwargs
            if function_calling:
                logger.info("\n" + pformat(function_calling))
        except:
            logger.warning("No function calling found")
        self.run_total_tools["llm"].append((dt.now() - self._timer).total_seconds())
        self.run_total_tokens.append(response.llm_output["token_usage"]["total_tokens"])

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> Any:
        """Run when tool starts running."""
        logger.info("TOOL STARTED")
        self.tool_history[kwargs["run_id"]] = {"name": serialized["name"], "input": input_str}
        self._pb.progress(self._current_step/self._steps, text=f"[{self._current_step+1}] Calling {serialized['name']} ...")
        self._timer = dt.now()

    def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        """Run when tool ends running."""
        logger.info("TOOL ENDED")
        self.run_total_tools[kwargs["name"]].append((dt.now() - self._timer).total_seconds())
        self.tool_history[kwargs["run_id"]]["output"] = output
        self._format_command(self.tool_history[kwargs["run_id"]], output, self._tabs[self._current_step])

    def _format_plan(self, plan):
        if type(plan) == str:
            plan = re.sub(r"\d+\.", "- ", plan)
            plan = plan.split('- ')
        if type(plan) == list:
            plan = "<ul>" + ''.join(["<li>" + p.replace('\n','').strip() + "</li>" for p in plan if len(p.strip()) > 0]) + "</ul>"
        return plan

    def _format_thoughts(self, response, container: st.container):
        if response is None:
            return
        markdown = f"""
    | thought | content |
    | ------: | ------- |
    | text | {response.text} |
    | reasoning | {response.reasoning} |
    | plan | {self._format_plan(response.plan)} |
    | criticism | {response.criticism} |
        """
        container.markdown(markdown, unsafe_allow_html=True)

    def _format_command(self, response: Dict, observation: str, container: st.container):
        markdown = f""" 
    |  command | args |
    |  ------- | ---- |
    | {response.get("name")} | {response.get("input")} |
    """
        container.markdown(markdown, unsafe_allow_html=False)
        container.write(try_loads(observation, True))
