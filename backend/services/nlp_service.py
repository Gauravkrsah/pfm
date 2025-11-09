import re
import json
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

class ExpenseParser:
    def __init__(self):
        self.categories = {
            'food': ['biryani', 'pizza', 'restaurant', 'meal', 'lunch', 'dinner', 'food', 'eat', 'cafe', 'snack', 'tea', 'coffee', 'breakfast', 'momo', 'momos', 'noodles', 'chowmein', 'chowmin', 'chow', 'ramen', 'pasta', 'rice', 'dal', 'curry', 'khana', 'khaana', 'chiya', 'chai', 'dudh', 'milk', 'bhat', 'daal', 'tarkari', 'sabji', 'machha', 'fish', 'chicken', 'mutton', 'buff', 'pork', 'egg', 'anda', 'roti', 'chapati', 'paratha', 'samosa', 'pakoda', 'chaat', 'lassi', 'lasi', 'juice', 'paani', 'water', 'drink', 'beverage'],
            'transport': ['petrol', 'fuel', 'taxi', 'uber', 'bus', 'train', 'auto', 'rickshaw', 'metro', 'flight', 'travel', 'tempo', 'microbus', 'bike', 'scooter', 'car', 'gaadi'],
            'groceries': ['grocery', 'groceries', 'vegetables', 'fruits', 'market', 'supermarket', 'store', 'milk', 'bread', 'apple', 'garlic', 'potato', 'onion', 'tomato', 'sabji', 'tarkari', 'fruits', 'phal', 'alu', 'pyaj', 'lasun', 'dhaniya', 'hariyo', 'green'],
            'shopping': ['clothes', 'shoes', 'shopping', 'shirt', 'dress', 'bag', 'accessories', 'kapada', 'jutta', 'chappals', 'sandals'],
            'utilities': ['electricity', 'water', 'internet', 'phone', 'mobile', 'wifi', 'bill', 'current', 'paani', 'net', 'recharge'],
            'entertainment': ['movie', 'game', 'party', 'cinema', 'show', 'concert', 'film', 'picture', 'khel'],
            'accommodation': ['hotel', 'stay', 'booking', 'resort', 'lodge', 'guest house', 'airbnb'],
            'rent': ['rent', 'house', 'apartment', 'room', 'ghar', 'kotha', 'bhada'],
            'loan': ['loan', 'lend', 'borrow', 'debt', 'rin', 'gave', 'diye', 'liye', 'udhar', 'qarz'],
            'income': ['salary', 'bonus', 'incentive', 'refund', 'income', 'earning', 'payment', 'received'],
            'education': ['admission', 'fee', 'tuition', 'school', 'college', 'university', 'course', 'class', 'book', 'study', 'education', 'exam', 'test']
        }
    
    def parse(self, text):
        expenses = []
        text = text.strip()
        
        # Split by comma or 'and' and process each part
        parts = re.split(r',|\band\b', text, flags=re.IGNORECASE)
        parts = [part.strip() for part in parts if part.strip()]
        
        for part in parts:
            expense = self._parse_single_expense(part)
            if expense:
                expenses.append(expense)
        
        reply = self._generate_reply(expenses)
        return expenses, reply
    
    def _parse_single_expense(self, text):
        """Parse a single expense from text with multiple pattern matching"""
        text = text.strip()
        
        # FIRST: Try simple "amount item" pattern (most common)
        simple_pattern = r'^(\d+)\s+(.+)$'
        simple_match = re.match(simple_pattern, text)
        if simple_match:
            amount, item = simple_match.groups()
            item = self._clean_item_name(item)
            category = self._categorize(item)
            return {
                'amount': int(amount),
                'item': item.lower(),
                'category': category,
                'remarks': item.title(),
                'paid_by': None
            }
        
        # Pattern 0d: "person owes amount to person" with fuzzy matching
        # Check this FIRST to catch debt patterns before other matches
        debt_keywords = r'(?:owes?|ows?|owe|owz|owse|debt|borrows?|lends?|udhar|qarz)'
        owes_pattern = rf'([a-zA-Z]+)\s+{debt_keywords}\s+(\d+)\s+(?:to|from)\s+([a-zA-Z]+)'
        owes_match = re.search(owes_pattern, text, re.IGNORECASE)
        if owes_match:
            debtor, amount, creditor = owes_match.groups()
            return {
                'amount': int(amount),
                'item': f'{debtor.lower()} owes {creditor.lower()}',
                'category': 'Loan',
                'remarks': f"{debtor.title()} owes {creditor.title()}",
                'paid_by': debtor.title()
            }
        
        # Pattern 0a: "got/received salary amount" like "got salary 100000" or "got salary today 50000"
        salary_pattern = r'^(?:got|received)\s+salary\s+(?:today\s+)?(\d+)$'
        salary_match = re.match(salary_pattern, text, re.IGNORECASE)
        if salary_match:
            amount = salary_match.group(1)
            return {
                'amount': -int(amount),  # Negative for income
                'item': 'salary',
                'category': 'Income',
                'remarks': 'Got Salary Today' if 'today' in text.lower() else 'Salary received',
                'paid_by': None
            }
        
        # Pattern 0b: "salary amount received" like "salary 100000 received"
        salary_pattern2 = r'^salary\s+(\d+)\s+(?:received|got)$'
        salary_match2 = re.match(salary_pattern2, text, re.IGNORECASE)
        if salary_match2:
            amount = salary_match2.group(1)
            return {
                'amount': -int(amount),  # Negative for income
                'item': 'salary',
                'category': 'Income',
                'remarks': 'Salary received',
                'paid_by': None
            }
        
        # Pattern 0c: General income patterns like "bonus 5000", "incentive 2000", "refund 1000"
        income_pattern = r'^(salary|bonus|incentive|refund|income|earning|payment|received)\s+(\d+)$'
        income_match = re.match(income_pattern, text, re.IGNORECASE)
        if income_match:
            income_type, amount = income_match.groups()
            return {
                'amount': -int(amount),  # Negative for income
                'item': income_type.lower(),
                'category': 'Income',
                'remarks': f'{income_type.title()} received',
                'paid_by': None
            }
        
        # Pattern 0d: "got back/received amount from person" like "got back 400 from sonu"
        repayment_pattern = r'^(?:got\s+back|received|returned)\s+(\d+)\s+from\s+([a-zA-Z]+)'
        repayment_match = re.match(repayment_pattern, text, re.IGNORECASE)
        if repayment_match:
            amount, person = repayment_match.groups()
            return {
                'amount': -int(amount),  # Negative for income
                'item': 'loan repayment',
                'category': 'Loan',
                'remarks': f"Loan repaid by {person.title()}",
                'paid_by': person.title()
            }
        
        # Pattern 1a: "gave person amount for duration" like "gave sonu 400 for a week"
        gave_duration_pattern = r'^(?:gave|lend|lent)\s+([a-zA-Z]+)\s+(\d+)\s+for\s+(.+)$'
        gave_duration_match = re.match(gave_duration_pattern, text, re.IGNORECASE)
        if gave_duration_match:
            person, amount, duration = gave_duration_match.groups()
            return {
                'amount': int(amount),
                'item': 'loan',
                'category': 'Loan',
                'remarks': f"Loan given to {person.title()} for {duration}",
                'paid_by': person.title()
            }
        
        # Pattern 1b: "gave person amount loan" like "gave gaurav 300 loan"
        loan_pattern = r'^(?:gave|lend|lent)\s+([a-zA-Z]+)\s+(\d+)\s*(?:loan|rin|udhar)?$'
        loan_match = re.match(loan_pattern, text, re.IGNORECASE)
        if loan_match:
            person, amount = loan_match.groups()
            return {
                'amount': int(amount),
                'item': 'loan',
                'category': 'Loan',
                'remarks': f"Loan given to {person.title()}",
                'paid_by': person.title()
            }
        
        # Pattern 1c: "loan paid amount" like "loan paid 400"
        loan_paid_pattern = r'^loan\s+paid\s+(\d+)$'
        loan_paid_match = re.match(loan_paid_pattern, text, re.IGNORECASE)
        if loan_paid_match:
            amount = loan_paid_match.group(1)
            return {
                'amount': int(amount),
                'item': 'loan given',
                'category': 'Loan',
                'remarks': 'Loan given',
                'paid_by': None
            }
        
        # Pattern 2: "item person amount" like "rent sonu 20000" or "tea gaurav 100"
        # Only match if it's clearly a person name (common names or single word after single-word item)
        common_item_words = ['case', 'cover', 'stand', 'holder', 'bag', 'box', 'pack', 'set', 'kit']
        food_words = ['lunch', 'dinner', 'breakfast', 'snack', 'meal', 'tea', 'coffee', 'food']
        pattern1 = r'^([a-zA-Z\s]+?)\s+([a-zA-Z]+)\s+(\d+)$'
        match1 = re.match(pattern1, text)
        if match1:
            item, potential_person, amount = match1.groups()
            # Skip if potential_person is likely part of item description
            if potential_person.lower() not in food_words and potential_person.lower() not in common_item_words:
                # Only treat as person if item is single word (like "rent", "tea")
                if len(item.split()) == 1:
                    item = self._clean_item_name(item)
                    category = self._categorize(item)
                    return {
                        'amount': int(amount),
                        'item': item.lower(),
                        'category': category,
                        'remarks': f"{item.title()} - Paid by {potential_person.title()}",
                        'paid_by': potential_person.title()
                    }
        
        # Pattern 3: "item for/on context amount" like "samosa for lunch 80"
        pattern2a = r'^([a-zA-Z\s]+?)\s+(?:for|on)\s+([a-zA-Z\s]+?)\s+(\d+)$'
        match2a = re.match(pattern2a, text)
        if match2a:
            item, context, amount = match2a.groups()
            full_item = f"{item} for {context}"
            item = self._clean_item_name(full_item)
            category = self._categorize(item)
            return {
                'amount': int(amount),
                'item': item.lower(),
                'category': category,
                'remarks': item.title(),
                'paid_by': None
            }
        
        # Pattern 3b: "amount for/on item" like "500 for petrol" or "100 on tea"
        pattern2 = r'^(\d+)\s+(?:for|on)\s+(?:the\s+)?(.+)$'
        match2 = re.match(pattern2, text)
        if match2:
            amount, item = match2.groups()
            item = self._clean_item_name(item)
            category = self._categorize(item)
            return {
                'amount': int(amount),
                'item': item.lower(),
                'category': category,
                'remarks': item.title(),
                'paid_by': None
            }
        
        # Pattern 4: "spend amount on item" like "spend 100 on tea"
        pattern3 = r'^spend\s+(\d+)\s+on\s+(?:the\s+)?(.+)$'
        match3 = re.match(pattern3, text, re.IGNORECASE)
        if match3:
            amount, item = match3.groups()
            item = self._clean_item_name(item)
            category = self._categorize(item)
            return {
                'amount': int(amount),
                'item': item.lower(),
                'category': category,
                'remarks': item.title()
            }
        
        # Pattern 4b: "paid/payed amount for item" like "paid 5000 for hotel"
        paid_pattern = r'^(?:paid|payed)\s+(\d+)\s+for\s+(?:the\s+)?(.+)$'
        paid_match = re.match(paid_pattern, text, re.IGNORECASE)
        if paid_match:
            amount, item = paid_match.groups()
            item = self._clean_item_name(item)
            category = self._categorize(item)
            return {
                'amount': int(amount),
                'item': item.lower(),
                'category': category,
                'remarks': item.title()
            }
        
        # Pattern 5: "amount spend on item" like "150 spend on momo"
        pattern3b = r'^(\d+)\s+spend\s+on\s+(?:the\s+)?(.+)$'
        match3b = re.match(pattern3b, text, re.IGNORECASE)
        if match3b:
            amount, item = match3b.groups()
            item = self._clean_item_name(item)
            category = self._categorize(item)
            return {
                'amount': int(amount),
                'item': item.lower(),
                'category': category,
                'remarks': item.title()
            }
        
        # Pattern 6a: "item - paid by person amount" like "Purchased Phone - Paid by Case 500"
        pattern4a = r'^(.+?)\s*-\s*paid\s+by\s+([a-zA-Z]+)\s+(\d+)$'
        match4a = re.match(pattern4a, text, re.IGNORECASE)
        if match4a:
            item, person, amount = match4a.groups()
            item = self._clean_item_name(item)
            category = self._categorize(item)
            return {
                'amount': int(amount),
                'item': item.lower(),
                'category': category,
                'remarks': f"{item.title()} - Paid by {person.title()}",
                'paid_by': person.title()
            }
        
        # Pattern 6: "item amount paid by person" like "rent 20000 paid by sonu"
        pattern4 = r'^([a-zA-Z\s]+?)\s+(\d+)\s+paid\s+by\s+([a-zA-Z]+)$'
        match4 = re.match(pattern4, text, re.IGNORECASE)
        if match4:
            item, amount, person = match4.groups()
            item = self._clean_item_name(item)
            category = self._categorize(item)
            return {
                'amount': int(amount),
                'item': item.lower(),
                'category': category,
                'remarks': f"{item.title()} - Paid by {person.title()}",
                'paid_by': person.title()
            }
        
        # Pattern 6b: "item cost/costs amount" like "fan cost 4000" or "ac costs 200000"
        cost_pattern = r'^([a-zA-Z\s]+?)\s+costs?\s+(\d+)$'
        cost_match = re.match(cost_pattern, text, re.IGNORECASE)
        if cost_match:
            item, amount = cost_match.groups()
            item = self._clean_item_name(item)
            category = self._categorize(item)
            return {
                'amount': int(amount),
                'item': item.lower(),
                'category': category,
                'remarks': item.title()
            }
        
        # Pattern 6c: "item of amount" like "Purchased Phone of 500"
        pattern4c = r'^(.+?)\s+of\s+(\d+)$'
        match4c = re.match(pattern4c, text, re.IGNORECASE)
        if match4c:
            item, amount = match4c.groups()
            item = self._clean_item_name(item)
            category = self._categorize(item)
            return {
                'amount': int(amount),
                'item': item.lower(),
                'category': category,
                'remarks': item.title()
            }
        
        # Pattern 7: "item amount" like "grocery 300" or "biryani 500"
        pattern5 = r'^([a-zA-Z\s]+?)\s+(\d+)$'
        match5 = re.match(pattern5, text)
        if match5:
            item, amount = match5.groups()
            # Special handling for loan transactions
            if item.lower().strip() == 'loan':
                return {
                    'amount': int(amount),
                    'item': 'loan given',
                    'category': 'Loan',
                    'remarks': 'Loan given',
                    'paid_by': None
                }
            
            item = self._clean_item_name(item)
            category = self._categorize(item)
            return {
                'amount': int(amount),
                'item': item.lower(),
                'category': category,
                'remarks': item.title(),
                'paid_by': None
            }
        
        # FALLBACK: Extract any number and treat rest as item
        number_match = re.search(r'(\d+)', text)
        if number_match:
            amount = int(number_match.group(1))
            # Remove the number and clean the remaining text
            item = re.sub(r'\d+', '', text).strip()
            if item:
                item = self._clean_item_name(item)
                category = self._categorize(item)
                return {
                    'amount': amount,
                    'item': item.lower(),
                    'category': category,
                    'remarks': item.title(),
                    'paid_by': None
                }
        
        # Fallback: Extract amount and treat rest as item
        amount_match = re.search(r'Rs\.?(\d+)|Rs.?(\d+)', text)
        if amount_match:
            amount = int(amount_match.group(1) or amount_match.group(2))
            description = re.sub(r'Rs\.?\d+|Rs.?\d+', '', text)
            description = re.sub(r'\b(on|for|spent|the|paid|by)\b', '', description, flags=re.IGNORECASE)
            description = re.sub(r'\s+', ' ', description).strip()
            description = self._clean_item_name(description)
            
            if description and amount > 0:
                category = self._categorize(description)
                return {
                    'amount': amount,
                    'item': description.lower(),
                    'category': category,
                    'remarks': description.title()
                }
        
        return None
    
    def _clean_item_name(self, item):
        """Clean and normalize item names"""
        item = item.strip()
        item = re.sub(r'\b(the|a|an)\b', '', item, flags=re.IGNORECASE)
        item = re.sub(r'\s+', ' ', item).strip()
        
        nepali_mappings = {
            'chowmin': 'chowmein', 'chow min': 'chowmein',
            'khana': 'food', 'khaana': 'food',
            'chiya': 'tea', 'chai': 'tea',
            'dudh': 'milk', 'paani': 'water',
            'bhat': 'rice', 'daal': 'dal',
            'tarkari': 'vegetables', 'sabji': 'vegetables',
            'machha': 'fish', 'anda': 'egg',
            'lasi': 'lassi', 'phal': 'fruits',
            'alu': 'potato', 'pyaj': 'onion',
            'kapada': 'clothes', 'jutta': 'shoes',
            'ghar': 'house', 'kotha': 'room',
            'gaadi': 'vehicle', 'current': 'electricity',
            'admission fee': 'admission fee', 'fee': 'fee'
        }
        
        item_lower = item.lower()
        for nepali, english in nepali_mappings.items():
            if nepali in item_lower:
                item = item_lower.replace(nepali, english)
                break
        
        return item
    
    def _categorize(self, description):
        description_lower = description.lower()
        
        # Check existing categories first
        for category, keywords in self.categories.items():
            if any(keyword in description_lower for keyword in keywords):
                return category.title()
        
        # Smart category creation for unknown items
        return self._smart_categorize(description_lower)
    
    def _smart_categorize(self, description):
        """Create intelligent categories for unknown items"""
        # Electronics & Appliances
        if any(word in description for word in ['fan', 'ac', 'tv', 'fridge', 'laptop', 'phone', 'mobile', 'computer', 'tablet', 'camera', 'speaker', 'headphone', 'charger', 'appliance', 'electronic']):
            return 'Electronics'
        
        # Travel & Accommodation
        if any(word in description for word in ['hotel', 'stay', 'booking', 'resort', 'lodge', 'airbnb', 'hostel']):
            return 'Travel'
        
        # Medical & Health
        if any(word in description for word in ['doctor', 'medicine', 'hospital', 'clinic', 'pharmacy', 'medical', 'health']):
            return 'Medical'
        
        # Education - Enhanced
        if any(word in description for word in ['admission', 'fee', 'tuition', 'school', 'college', 'university', 'course', 'class', 'book', 'study', 'education', 'exam', 'test']):
            return 'Education'
        
        # Beauty & Personal Care
        if any(word in description for word in ['salon', 'haircut', 'beauty', 'cosmetic', 'spa', 'massage']):
            return 'Personal Care'
        
        # Gifts & Donations
        if any(word in description for word in ['gift', 'present', 'donation', 'charity', 'birthday']):
            return 'Gifts'
        
        # Insurance & Finance
        if any(word in description for word in ['insurance', 'premium', 'policy', 'bank', 'fee', 'charge']):
            return 'Finance'
        
        # Maintenance & Repair
        if any(word in description for word in ['repair', 'fix', 'maintenance', 'service', 'cleaning']):
            return 'Maintenance'
        
        # Sports & Fitness
        if any(word in description for word in ['gym', 'fitness', 'sport', 'exercise', 'yoga', 'swimming']):
            return 'Fitness'
        
        # Food/Drinks - catch common items
        if any(word in description for word in ['chiya', 'chai', 'tea', 'coffee', 'drink', 'beverage', 'snack']):
            return 'Food'
        
        return 'Other'
    
    def _generate_reply(self, expenses):
        if not expenses:
            return "ERROR: No expenses found. Try: '500 on biryani, 400 on grocery'"
        
        reply_parts = []
        for expense in expenses:
            amount = expense['amount']
            if amount < 0:  # Income
                reply_parts.append(f"SUCCESS: Added Rs.{abs(amount)} -> {expense['category']} ({expense['remarks']})")
            else:  # Expense
                reply_parts.append(f"SUCCESS: Added Rs.{amount} -> {expense['category']} ({expense['remarks']})")
        
        return '\n'.join(reply_parts)

class NLPService:
    def __init__(self):
        self.parser = ExpenseParser()
        self._setup_gemini()
        # Initialize RAG service
        try:
            from services.rag_service import RAGService
            self.rag_service = RAGService()
        except Exception as e:
            print(f"RAG Service initialization failed: {e}")
            self.rag_service = None
    
    def _setup_gemini(self):
        """Setup Gemini AI with error handling"""
        self.gemini_available = False
        self.model = None
        
        if not GENAI_AVAILABLE:
            print("WARNING: google-generativeai not installed")
            return
        
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if gemini_api_key and gemini_api_key.strip():
            try:
                genai.configure(api_key=gemini_api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash')
                self.gemini_available = True
                print("SUCCESS: Gemini API configured")
            except Exception as e:
                print(f"ERROR: Gemini API setup failed: {e}")
    
    def get_gemini_response(self, prompt: str) -> Optional[str]:
        """Get response from Gemini with error handling"""
        if not self.model or not self.gemini_available:
            return None
        
        try:
            response = self.model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"Gemini API error: {e}")
        
        return None
    
    async def _ai_enhanced_parse(self, text):
        """Use AI to intelligently parse expense text"""
        try:
            prompt = f"""
You are an intelligent expense parser. Parse this text into structured expense data.

Text: "{text}"

Rules:
1. ALWAYS extract expenses from ANY text that mentions money/amounts
2. Be flexible - understand context and intent, not just exact patterns
3. Handle simple formats like "100 chiya", "300 admission fee", "50 tea"
4. Categories: Food, Transport, Groceries, Shopping, Utilities, Entertainment, Rent, Loan, Income, Medical, Education, Travel, Other
5. Income (negative amounts): salary, bonus, refund, got back, received
6. Loans:
   - "gave/lend to person" = POSITIVE amount (you gave loan)
   - "taken/borrowed from person" = NEGATIVE amount (you took loan)
   - "paid person" or "paid person's loan" = POSITIVE amount (you repaid loan)
   - "received from person" = NEGATIVE amount (they repaid you)

Examples:
- "100 chiya" → {{"amount": 100, "item": "chiya", "category": "Food", "remarks": "Chiya"}}
- "300 admission fee" → {{"amount": 300, "item": "admission fee", "category": "Education", "remarks": "Admission Fee"}}
- "50 tea" → {{"amount": 50, "item": "tea", "category": "Food", "remarks": "Tea"}}
- "500 on biryani" → {{"amount": 500, "item": "biryani", "category": "Food", "remarks": "Biryani"}}
- "gave sonu 400" → {{"amount": 400, "item": "loan", "category": "Loan", "remarks": "Loan given to Sonu", "paid_by": "Sonu"}}
- "taken loan from munchun 4000" → {{"amount": -4000, "item": "loan", "category": "Loan", "remarks": "Loan taken from Munchun", "paid_by": "Munchun"}}
- "paid munchun 3000" → {{"amount": 3000, "item": "loan repayment", "category": "Loan", "remarks": "Loan repaid to Munchun", "paid_by": "Munchun"}}
- "got salary 50000" → {{"amount": -50000, "item": "salary", "category": "Income", "remarks": "Salary received"}}

IMPORTANT:
- If you find ANY amount and item, create an expense entry
- For loans: "taken from" = NEGATIVE, "gave to" = POSITIVE, "paid to" = POSITIVE
- Don't be strict about format

Return ONLY valid JSON:
{{
  "expenses": [
    {{"amount": 100, "item": "chiya", "category": "Food", "remarks": "Chiya", "paid_by": null}}
  ],
  "reply": "SUCCESS: Added Rs.100 -> Food (Chiya)"
}}
"""
            
            response = self.get_gemini_response(prompt)
            if response:
                # Clean response and extract JSON
                response = response.strip()
                if response.startswith('```json'):
                    response = response[7:-3]
                elif response.startswith('```'):
                    response = response[3:-3]
                
                # Find JSON in response
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    parsed_data = json.loads(json_str)
                    
                    # Validate and fix structure
                    if 'expenses' in parsed_data:
                        if 'reply' not in parsed_data:
                            count = len(parsed_data['expenses'])
                            total = sum(exp.get('amount', 0) for exp in parsed_data['expenses'])
                            parsed_data['reply'] = f"SUCCESS: Added {count} expenses totaling Rs.{total}"
                        return parsed_data
            
            return None
            
        except Exception as e:
            print(f"[AI_PARSE] Error: {e}")
            return None
    
    async def parse_expense(self, text: str):
        """Parse expense text and return structured data"""
        try:
            print(f"[PARSE] Processing: {text}")
            
            # Try AI-enhanced parsing first if Gemini is available
            if self.gemini_available:
                print(f"[PARSE] Trying AI parsing...")
                ai_result = await self._ai_enhanced_parse(text)
                if ai_result and ai_result.get('expenses'):
                    print(f"[PARSE] AI successfully parsed {len(ai_result['expenses'])} expenses")
                    return ai_result
                else:
                    print(f"[PARSE] AI parsing failed, falling back to rule-based")
            
            # Fallback to rule-based parser
            print(f"[PARSE] Using rule-based parser")
            expenses, reply = self.parser.parse(text)
            
            # If rule-based fails, try simple extraction
            if not expenses:
                print(f"[PARSE] Rule-based failed, trying simple extraction")
                simple_expense = self._simple_extract(text)
                if simple_expense:
                    expenses = [simple_expense]
                    reply = f"SUCCESS: Added Rs.{simple_expense['amount']} -> {simple_expense['category']} ({simple_expense['remarks']})"
            
            return {
                "expenses": expenses,
                "reply": reply
            }
            
        except Exception as e:
            print(f"[ERROR] Parse error: {e}")
            return {
                "expenses": [],
                "reply": f"ERROR: Error parsing expenses: {str(e)}"
            }
    
    def _simple_extract(self, text):
        """Simple extraction as last resort"""
        try:
            # Find any number in the text
            number_match = re.search(r'(\d+)', text)
            if number_match:
                amount = int(number_match.group(1))
                # Remove number and clean text for item
                item = re.sub(r'\d+', '', text).strip()
                if not item:
                    item = 'expense'
                
                # Clean item name
                item = self.parser._clean_item_name(item)
                category = self.parser._categorize(item)
                
                return {
                    'amount': amount,
                    'item': item.lower(),
                    'category': category,
                    'remarks': item.title(),
                    'paid_by': None
                }
        except Exception as e:
            print(f"[SIMPLE_EXTRACT] Error: {e}")
        return None
    
    def _parse_multi_expenses(self, text):
        """Parse multiple expenses from comma-separated format"""
        try:
            parts = [p.strip() for p in text.split(',')]
            expenses = []
            
            i = 0
            while i < len(parts):
                amount_part = None
                amount = None
                
                # Look for Rs.Amount pattern
                for j in range(i, min(i + 3, len(parts))):
                    if re.search(r'Rs\.?(\d+)', parts[j], re.IGNORECASE):
                        amount_match = re.search(r'Rs\.?(\d+)', parts[j], re.IGNORECASE)
                        amount = int(amount_match.group(1))
                        amount_part = j
                        break
                
                if amount is None:
                    i += 1
                    continue
                
                # Get item (before amount)
                item = parts[i] if i < amount_part else 'item'
                
                # Get category (after amount)
                category = parts[amount_part + 1] if amount_part + 1 < len(parts) else 'Other'
                
                # Clean up
                item = re.sub(r'Rs\.?\d+', '', item, flags=re.IGNORECASE).strip()
                category = re.sub(r'Rs\.?\d+', '', category, flags=re.IGNORECASE).strip()
                
                if not item:
                    item = 'item'
                if not category:
                    category = 'Other'
                
                expenses.append({
                    'amount': amount,
                    'item': item.lower(),
                    'category': category.title(),
                    'remarks': item.title(),
                    'paid_by': None
                })
                
                i = amount_part + 2
            
            return expenses if expenses else None
            
        except Exception as e:
            print(f"[MULTI_PARSE] Error: {e}")
            return None
    
    async def chat_about_expenses(self, request):
        """Handle chat requests about expenses using RAG with Gemini"""
        try:
            from services.expense_analyzer import ExpenseAnalyzer
            
            analyzer = ExpenseAnalyzer()
            
            # Extract user name
            user_name = "there"
            if request.user_name and str(request.user_name).strip():
                user_name = str(request.user_name).strip()
            elif request.user_email:
                email_name = request.user_email.split('@')[0]
                user_name = email_name.capitalize()
            
            # Determine context and prepare data
            is_group_mode = bool(request.group_name and request.group_expenses_data)
            table_data = request.group_expenses_data if is_group_mode else (request.expenses_data or [])
            context_type = f"group '{request.group_name}'" if is_group_mode else "personal"
            
            if not table_data:
                response = f"Hi {user_name}! You don't have any {context_type} expenses recorded yet. Start by adding some expenses to get insights!"
                return {"reply": response}
            
            # Try RAG service first (enhanced with better context)
            if self.rag_service and self.rag_service.gemini_available:
                print(f"[CHAT] Using RAG service for query: {request.text}")
                rag_response = await self.rag_service.query_expenses(request.text, table_data, user_name)
                if rag_response:
                    print(f"[CHAT] RAG service provided response")
                    return {"reply": rag_response}
                else:
                    print(f"[CHAT] RAG service failed, trying legacy Gemini")
            
            # Analyze expenses for fallback
            analysis = analyzer.analyze_expenses(table_data)
            
            # Try legacy Gemini RAG if RAG service unavailable
            if self.gemini_available and not (self.rag_service and self.rag_service.gemini_available):
                print(f"[CHAT] Using legacy Gemini RAG")
                gemini_response = await self._gemini_rag_query(request.text, table_data, analysis, user_name)
                if gemini_response:
                    return {"reply": gemini_response}
            
            # Fallback to rule-based processing
            print(f"[CHAT] Using rule-based analyzer")
            processed_response = analyzer.process_query(request.text, analysis, context_type, table_data)
            final_response = f"Hi {user_name}! {processed_response}"
            return {"reply": final_response}
            
        except Exception as e:
            print(f"[ERROR] Chat error: {e}")
            error_name = user_name if 'user_name' in locals() else 'there'
            return {
                "reply": f"Hi {error_name}! Sorry, I encountered an error processing your question. Please try again.",
                "error": True
            }
    
    async def _gemini_rag_query(self, query: str, expenses_data: list, analysis: dict, user_name: str) -> Optional[str]:
        """Use Gemini with RAG (Retrieval Augmented Generation) for intelligent responses"""
        try:
            # Prepare structured data summary
            categories_summary = "\n".join([f"  - {cat.title()}: Rs.{amount}" for cat, amount in analysis['categories'].items()])
            
            # Get recent transactions
            recent_txns = expenses_data[:10] if len(expenses_data) > 10 else expenses_data
            transactions_text = "\n".join([
                f"  - Rs.{txn.get('amount', 0)} on {txn.get('item', 'item')} ({txn.get('category', 'Other')}) on {txn.get('date', 'N/A')}"
                for txn in recent_txns
            ])
            
            prompt = f"""
You are a personal finance assistant. Answer the user's question based on their financial data.

User: {user_name}
Query: "{query}"

FINANCIAL DATA:

Total Expenses: Rs.{analysis['total']}
Total Transactions: {analysis['count']}
Income: Rs.{analysis.get('total_income', 0)}
Net Balance: Rs.{analysis.get('net_balance', 0)}

Category Breakdown:
{categories_summary}

Recent Transactions:
{transactions_text}

INSTRUCTIONS:
1. Answer naturally and conversationally
2. Use the exact numbers from the data provided
3. If asked about multiple categories (e.g., "food and grocery"), combine the totals
4. Start response with "Hi {user_name}!"
5. Be concise but informative
6. If data is missing, say so politely

Provide a helpful, accurate response:
"""
            
            response = self.get_gemini_response(prompt)
            if response:
                return response.strip()
            
            return None
            
        except Exception as e:
            print(f"[GEMINI_RAG] Error: {e}")
            return None