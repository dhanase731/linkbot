"""
Database models for Chat Application
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from bson import ObjectId


class Message(BaseModel):
    """Chat message model"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Conversation(BaseModel):
    """Conversation/Chat model"""
    id: Optional[str] = Field(None, alias="_id")
    title: str
    messages: List[Message] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: str = "default"  # For multi-user support in future
    
    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            ObjectId: lambda v: str(v)
        }


class ChatRequest(BaseModel):
    """Request to chat"""
    conversation_id: Optional[str] = None
    message: str
    model: Optional[str] = "gpt-3.5-turbo"  # or "local"


class ChatResponse(BaseModel):
    """Response from chat"""
    success: bool
    conversation_id: str
    title: str
    message: Message
    all_messages: List[Message] = []
    error: Optional[str] = None


class ConversationListItem(BaseModel):
    """Simplified conversation for list view"""
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            ObjectId: lambda v: str(v)
        }


class ScrapeRequest(BaseModel):
    """Request to scrape a website"""
    url: str
    timeout: int = 30
    wait_for_selector: Optional[str] = None
    extract_full_text: bool = True
    extract_links: bool = False
    custom_selectors: Optional[dict] = None


class ParagraphSummarizationRequest(BaseModel):
    """Request to summarize a paragraph"""
    paragraph: str
    style: str = "concise"  # "concise", "detailed", "bullet-points", "academic"
    max_length: Optional[int] = None


class WebsiteAnalysisRequest(BaseModel):
    """Request for comprehensive website analysis"""
    url: str
    analyze_tech_stack: bool = True
    analyze_apis: bool = True
    analyze_purpose: bool = True
    detailed: bool = False
