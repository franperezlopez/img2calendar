import json
from pathlib import Path
from typing import Any, Optional

from langchain.tools import BaseTool
from langchain.tools.shell.tool import ShellTool

from src.tools.scraper import scrape
from src.utils import cached


class Playwright(BaseTool):
    name = "playwright"
    description = "recommended for web scraping"
    tool : Optional[ShellTool]
    command: Optional[str]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tool = ShellTool()
        playw_path = Path(__file__).parent.parent.parent.absolute()
        self.command = f"docker run -v {playw_path}:/mnt/playw --rm --ipc=host --user pwuser --security-opt seccomp={playw_path / 'seccomp_profile.json'} mcr.microsoft.com/playwright:latest node /mnt/playw/app.js {{url}}"

    @cached(key_func_name="playwright")
    def _run(self, url: str) -> str:
        """Run query through Playwright and return json string containing page title and body."""
        page = self.tool.run({"commands": [self.command.format(url=url)]})
        return self._scrape(page)

    def _scrape(self, content: str) -> str:
        page = json.loads(content)
        page["body"] = scrape(page["body"])
        return json.dumps(page)
    async def _arun(self, url: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("Playwright does not support async")    