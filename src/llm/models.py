from typing import List, Optional, Dict, Any
from enum import Enum

from langchain.pydantic_v1 import BaseModel, Field

class Thoughts(BaseModel):
    """Reasoning process"""
    text: str = Field(..., description="thoughts")
    reasoning: str = Field(..., description="reasoning scratchpad")
    plan: str = Field(..., description="short bulleted list that conveys your goals")
    criticism: str = Field(..., description="optional constructive self-criticism")

class Command(BaseModel):
    """Command to execute"""
    # attribute: str = Field(..., description="event attribute aimed to be queried")
    name: str = Field(..., description="command name")
    args: Optional[List[str]] = Field(description="command arguments")
    #args: Optional[Dict[str, Any]] = Field(description="args value must be a dictionary {'arg name': 'value'}")

class UnkownEvent(BaseModel):
    class EventKind(str, Enum):
        unknown = Field(..., description="default value; until certain, consider the event as unknown")
        technology = Field(..., description="event is a technology event")
        music = Field(..., description="event is a music event")
        other = Field(..., description="other kind of event or is not an event")
    information: str = Field(..., description="all information gathered about the event")
    kind:EventKind = Field(..., description="event kind")

class Event(BaseModel):
    """Basic event model"""
    name: str = Field(..., description="represents the title or designation of the event")
    date: str = Field(description="versatile field that accommodates various forms of date and time inputs of the event", default="current year")
    location: Optional[str] = Field(description=" general idea of where the event is taking place")
    address: Optional[str] = Field(description="location of the event")
    city: Optional[str] = Field(description="city of the event")
    description: Optional[str] = Field(description="event description. include extra information not mentioned before. include relevant URLs")

class Action(BaseModel):
    """Self-explanatory command"""
    # event: Event = Field(..., description="collected data from the event")
    event: str = Field(..., description="represents the title or designation of the event")
    thoughts: Thoughts = Field(..., description="explain your reasoning process")
    command: Optional[Command] = Field(description="next command to be executed, only provided if the process is not finished")
    iCalendar: Optional[str] = Field(description="event using iCalendar format. only provided when the process is finished")

class iCalendar(BaseModel):
    # thoughts: Thoughts = Field(..., description="explain your reasoning process")
    iCalendar: str = Field(description="event using iCalendar format")

class TalkEvent(Event):
    speaker: List[str] = Field(..., description="event speaker/s")
    topics: Optional[List[str]] = Field(..., description="event topics / technologies")

class ConferenceEvent(Event):
    talks: List[str] = Field(..., description="conference talks")
    end_time: str = Field(..., description="festival end time")

class TechEvent(TalkEvent):
    host: str = Field(..., description="event host / organizer / company")

class MusicEvent(Event):
    artist: str = Field(..., description="event artist")

class FestivalEvent(Event):
    performances: List[MusicEvent] = Field(..., description="bands/artists performing at the festival")
    end_time: str = Field(..., description="festival end time")
