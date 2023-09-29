from typing import Any, Optional, Type

from langchain.tools import BaseTool
from PIL import Image
from pydantic import BaseModel, Field
from transformers import Pix2StructForConditionalGeneration, Pix2StructProcessor


class VQAArgumentsSchema(BaseModel):
    question : str = Field(description="question to ask to the image. the function is sensible to interrogation types (what,where,when,kind)")

class VQA(BaseTool):
    name = "vqa"
    description = "useful when you need to answer questions on images"
    args_schema: Type[VQAArgumentsSchema] = VQAArgumentsSchema

    PATH_TO_SAVE = "google/pix2struct-docvqa-large" # '../models/pix2struct/docvqa-larg'
    device : Optional[str] = None
    model : Optional[Pix2StructForConditionalGeneration] = None
    processor : Optional[Pix2StructProcessor] = None
    image : Optional[Image.Image] = None
    def __init__(self, device: str ="cuda"):
        super().__init__()
        self.device = device
        self.model, self.processor = self._load_tool()

    def _load_tool(self):
        model = Pix2StructForConditionalGeneration.from_pretrained(self.PATH_TO_SAVE).to(self.device)
        processor = Pix2StructProcessor.from_pretrained(self.PATH_TO_SAVE)
        return model, processor

    def _run(self, question: str) -> str:
        inputs = self.processor(images=self.image, text=question, return_tensors="pt").to(self.device)
        predictions = self.model.generate(**inputs)
        return self.processor.decode(predictions[0], skip_special_tokens=True)

    async def _arun(self, question: str) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("Google Search does not support async")

