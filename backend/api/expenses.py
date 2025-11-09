from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from services.nlp_service import NLPService
from services.expense_analyzer import ExpenseAnalyzer

router = APIRouter(tags=["expenses"])

class ParseRequest(BaseModel):
    text: str

class ChatRequest(BaseModel):
    text: str
    user_id: str = None
    user_email: str = None
    user_name: str = None
    expenses_data: list = []
    group_name: str = None
    group_expenses_data: list = []

# Initialize services
nlp_service = NLPService()
expense_analyzer = ExpenseAnalyzer()

@router.post("/parse")
async def parse_expense(request: ParseRequest):
    """Parse expense text and return structured expense data"""
    return await nlp_service.parse_expense(request.text)

@router.post("/chat")
async def chat_about_expenses(request: ChatRequest):
    """Chat about expenses with AI assistance"""
    print(f"[API] Chat request: {request.text}")
    print(f"[API] Expenses data count: {len(request.expenses_data)}")
    result = await nlp_service.chat_about_expenses(request)
    print(f"[API] Response: {result.get('reply', '')[:100]}...")
    return result