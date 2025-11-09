import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None

load_dotenv()

class RAGService:
    """RAG (Retrieval Augmented Generation) service for intelligent expense queries"""
    
    def __init__(self):
        self._setup_gemini()
    
    def _setup_gemini(self):
        """Setup Gemini AI"""
        self.gemini_available = False
        self.model = None
        
        if not GENAI_AVAILABLE:
            print("[X] RAG Service: google-generativeai not installed")
            return
        
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if gemini_api_key and gemini_api_key.strip():
            try:
                genai.configure(api_key=gemini_api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
                self.gemini_available = True
                print("[OK] RAG Service: Gemini configured")
            except Exception as e:
                print(f"[X] RAG Service: Gemini setup failed: {e}")
    
    def _prepare_expense_context(self, expenses_data: List[Dict]) -> str:
        """Prepare structured expense data for RAG"""
        if not expenses_data:
            return "No expense data available."
        
        # Separate expenses, income, and loans
        expenses = [e for e in expenses_data if e.get('amount', 0) > 0 and e.get('category', '').lower() not in ['income', 'loan']]
        income = [e for e in expenses_data if e.get('category', '').lower() == 'income' or (e.get('amount', 0) < 0 and e.get('category', '').lower() != 'loan')]
        loans = [e for e in expenses_data if e.get('category', '').lower() == 'loan']
        
        # Build context
        context_parts = []
        
        # Summary stats (excluding loans from expenses/income)
        total_expense = sum(e.get('amount', 0) for e in expenses)
        total_income = sum(abs(e.get('amount', 0)) for e in income)
        net_balance = total_income - total_expense
        
        context_parts.append(f"Total Expenses (excluding loans): Rs.{total_expense}")
        context_parts.append(f"Total Income: Rs.{total_income}")
        context_parts.append(f"Net Balance (Income - Expenses): Rs.{net_balance}")
        context_parts.append(f"Savings Rate: {int((net_balance/total_income*100) if total_income > 0 else 0)}%")
        
        # Category breakdown
        categories = {}
        for exp in expenses:
            cat = exp.get('category', 'Other')
            categories[cat] = categories.get(cat, 0) + exp.get('amount', 0)
        
        if categories:
            context_parts.append("\nCategory Breakdown:")
            for cat, amt in sorted(categories.items(), key=lambda x: x[1], reverse=True):
                count = len([e for e in expenses if e.get('category') == cat])
                context_parts.append(f"  {cat}: Rs.{amt} ({count} transactions)")
        
        # Loan breakdown by person (already filtered above)
        if loans:
            context_parts.append("\nLoan Details by Person:")
            person_loans = {}
            for loan in loans:
                person = loan.get('paid_by', '').lower().strip()
                amt = loan.get('amount', 0)
                print(f"[RAG DEBUG] Loan: person={person}, amount={amt}, item={loan.get('item')}")
                
                if person:
                    # Normalize: remove common variations and use fuzzy matching
                    person_clean = person.replace('s', '').replace('n', '')[:3]
                    
                    # Find existing similar person
                    person_normalized = None
                    for existing_key in person_loans.keys():
                        existing_clean = existing_key.replace('s', '').replace('n', '')[:3]
                        if person_clean == existing_clean:
                            person_normalized = existing_key
                            break
                    
                    if not person_normalized:
                        person_normalized = person
                    
                    if person_normalized not in person_loans:
                        person_loans[person_normalized] = {'given': 0, 'taken': 0, 'original_name': person}
                    else:
                        # Update original name to most recent
                        person_loans[person_normalized]['original_name'] = person
                    
                    if amt > 0:
                        person_loans[person_normalized]['given'] += amt
                    else:
                        person_loans[person_normalized]['taken'] += abs(amt)
            
            for person_key, amounts in person_loans.items():
                person_name = amounts['original_name'].title()
                given = amounts['given']
                taken = amounts['taken']
                
                print(f"[RAG CALC] Person: {person_name} (key={person_key}), Given: {given}, Taken: {taken}, Net: {taken-given if taken>given else given-taken}")
                
                if taken > given:
                    # You took more than you gave back = You owe them
                    net_owed = taken - given
                    context_parts.append(f"  {person_name}: Borrowed Rs.{taken} from them, Repaid Rs.{given} = YOU OWE Rs.{net_owed}")
                elif given > taken:
                    # You gave more than you took = They owe you
                    net_owed = given - taken
                    context_parts.append(f"  {person_name}: Lent Rs.{given} to them, Received back Rs.{taken} = THEY OWE Rs.{net_owed}")
                else:
                    context_parts.append(f"  {person_name}: Settled (borrowed Rs.{taken}, repaid Rs.{given})")
        
        # Recent transactions (last 15)
        recent = expenses_data[:15]
        if recent:
            context_parts.append("\nRecent Transactions:")
            for exp in recent:
                amt = exp.get('amount', 0)
                item = exp.get('item', 'item')
                cat = exp.get('category', 'Other')
                date = exp.get('date', 'N/A')
                paid_by = exp.get('paid_by', '')
                
                paid_info = f" (paid by {paid_by})" if paid_by else ""
                context_parts.append(f"  Rs.{amt} - {item} [{cat}] on {date}{paid_info}")
        
        context_str = "\n".join(context_parts)
        return context_str
    
    async def query_expenses(self, query: str, expenses_data: List[Dict], user_name: str = "there") -> Optional[str]:
        """Query expenses using RAG with Gemini"""
        if not self.gemini_available or not self.model:
            return None
        
        try:
            # Prepare context from expense data
            expense_context = self._prepare_expense_context(expenses_data)
            
            # Build RAG prompt
            prompt = f"""You are a personal finance assistant analyzing expense data.

USER: {user_name}
QUERY: "{query}"

EXPENSE DATA:
{expense_context}

INSTRUCTIONS:
1. Answer the user's question accurately using ONLY the data provided above
2. Be conversational and friendly - start with "Hi {user_name}!"
3. Use exact numbers from the data
4. If asked about multiple categories (e.g., "food and grocery"), combine totals
5. For LOAN queries:
   - Use ONLY the "Loan Details by Person" section - it has accurate net calculations
   - Look for "YOU OWE" or "THEY OWE" in the loan details
   - Person names may vary slightly - they refer to the same person
   - Answer with the exact amount from the loan details
6. For INCOME/BALANCE queries:
   - "Income remaining" = Net Balance = Total Income - Total Expenses
   - "How much money left" = Net Balance
   - "Available money" = Net Balance
   - Do NOT confuse with loans
7. If data is missing or unclear, say so politely
8. Format currency as Rs.X
9. Be concise but informative

Provide a helpful response:"""
            
            # Get Gemini response
            response = self.model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
            
            return None
            
        except Exception as e:
            print(f"[RAG] Query error: {e}")
            return None
    
    async def smart_categorize(self, item_description: str) -> Optional[str]:
        """Use Gemini to intelligently categorize an expense"""
        if not self.gemini_available or not self.model:
            return None
        
        try:
            prompt = f"""Categorize this expense item into ONE category:

Item: "{item_description}"

Categories: Food, Transport, Groceries, Shopping, Utilities, Entertainment, Rent, Loan, Income, Medical, Education, Travel, Electronics, Personal Care, Fitness, Other

Return ONLY the category name, nothing else."""
            
            response = self.model.generate_content(prompt)
            if response and response.text:
                category = response.text.strip()
                return category
            
            return None
            
        except Exception as e:
            print(f"[RAG] Categorize error: {e}")
            return None
