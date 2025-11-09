from typing import List, Dict, Any
from datetime import datetime, timedelta
import re

class ExpenseAnalyzer:
    """Advanced expense analysis and query processing"""

    def __init__(self):
        self.months = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
        self.categories = {
            'food': ['food', 'biryani', 'pizza', 'restaurant', 'hotel', 'meal', 'lunch', 'dinner', 'eat', 'cafe', 'snack', 'breakfast', 'tea', 'coffee', 'momo', 'chicken', 'lassi', 'chiya', 'chai'],
            'groceries': ['grocery', 'groceries', 'vegetables', 'fruits', 'market', 'supermarket', 'store', 'milk', 'bread'],
            'transport': ['petrol', 'fuel', 'taxi', 'uber', 'bus', 'train', 'auto', 'rickshaw', 'metro', 'flight', 'travel'],
            'shopping': ['clothes', 'shoes', 'shopping', 'shirt', 'dress', 'bag', 'accessories'],
            'utilities': ['electricity', 'water', 'internet', 'phone', 'mobile', 'wifi', 'bill'],
            'entertainment': ['movie', 'game', 'party', 'cinema', 'show', 'concert', 'entertainment'],
            'rent': ['rent', 'house', 'apartment', 'room'],
            'medical': ['doctor', 'medicine', 'hospital', 'medical', 'health', 'pharmacy'],
            'other': []
        }

    def analyze_expenses(self, expenses_data: List[Dict]) -> Dict[str, Any]:
        """Comprehensive analysis of expense data"""
        if not expenses_data:
            return {
                'total': 0,
                'count': 0,
                'categories': {},
                'recent_expenses': [],
                'top_categories': [],
                'average_per_day': 0,
                'total_income': 0,
                'income_count': 0,
                'net_balance': 0
            }

        # Separate expenses and income
        expenses = [exp for exp in expenses_data if exp.get('amount', 0) > 0 and exp.get('category', '').lower() != 'income']
        income_transactions = [exp for exp in expenses_data if exp.get('amount', 0) < 0 or exp.get('category', '').lower() == 'income']
        
        total_expenses = sum(exp.get('amount', 0) for exp in expenses)
        total_income = sum(abs(exp.get('amount', 0)) for exp in income_transactions)
        
        expense_count = len(expenses)
        income_count = len(income_transactions)
        
        net_balance = total_income - total_expenses

        # Category breakdown (only expenses)
        categories = {}
        for exp in expenses:
            category = exp.get('category', 'Other').lower()
            categories[category] = categories.get(category, 0) + exp.get('amount', 0)

        # Sort categories by amount
        top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]

        # Recent expenses (last 5 expenses only)
        recent_expenses = expenses[:5] if len(expenses) >= 5 else expenses

        # Calculate average per day (assuming data spans multiple days)
        dates = set()
        for exp in expenses_data:
            date_val = exp.get('date') or exp.get('created_at')
            if date_val:
                # Handle different date formats
                if isinstance(date_val, str):
                    # Extract date part if it's a datetime string
                    date_part = date_val.split('T')[0] if 'T' in date_val else date_val.split(' ')[0]
                    dates.add(date_part)
                else:
                    dates.add(str(date_val))

        days_count = len(dates) if dates else 1
        average_per_day = total_expenses / days_count if days_count > 0 else 0

        return {
            'total': total_expenses,
            'count': expense_count,
            'categories': categories,
            'recent_expenses': recent_expenses,
            'top_categories': top_categories,
            'average_per_day': round(average_per_day, 2),
            'days_tracked': days_count,
            'total_income': total_income,
            'income_count': income_count,
            'net_balance': net_balance
        }

    def find_specific_item(self, query: str, expenses_data: List[Dict]) -> Dict[str, Any]:
        """Find specific item expenses from the data"""
        query_lower = query.lower()
        
        # Extract potential item names from query
        item_keywords = []
        words = query_lower.split()
        
        # Words that indicate aggregate queries, not specific items
        aggregate_keywords = ['total', 'all', 'everything', 'overall', 'sum', 'entire', 'whole', 'complete']
        
        # Look for "on [item]" or "for [item]" patterns
        for i, word in enumerate(words):
            if word in ['on', 'for', 'spend', 'spent'] and i + 1 < len(words):
                next_word = words[i + 1]
                # Skip if next word is an aggregate keyword
                if next_word not in aggregate_keywords:
                    item_keywords.append(next_word)
        
        # Also check for direct item mentions
        common_items = ['momo', 'biryani', 'tea', 'coffee', 'lunch', 'dinner', 'grocery', 'petrol', 'taxi', 'rent', 'chicken', 'lassi', 'dahi', 'ghee', 'chiya']
        for item in common_items:
            if item in query_lower:
                item_keywords.append(item)
        
        if not item_keywords:
            return None
            
        # Find matching expenses
        matching_expenses = []
        total_amount = 0
        
        for expense in expenses_data:
            item_name = expense.get('item', '').lower()
            remarks = expense.get('remarks', '').lower()
            
            # Check if any keyword matches item or remarks
            for keyword in item_keywords:
                if keyword in item_name or keyword in remarks:
                    matching_expenses.append(expense)
                    total_amount += expense.get('amount', 0)
                    break
        
        if matching_expenses:
            return {
                'item_name': item_keywords[0],
                'total_amount': total_amount,
                'count': len(matching_expenses),
                'expenses': matching_expenses
            }
        
        return None

    def filter_by_date_range(self, expenses_data: List[Dict], start_date: datetime = None, end_date: datetime = None) -> List[Dict]:
        """Filter expenses by date range"""
        if not expenses_data:
            return []
        
        filtered = []
        for exp in expenses_data:
            date_val = exp.get('date') or exp.get('created_at')
            if not date_val:
                continue
            
            try:
                # Parse date string
                if isinstance(date_val, str):
                    date_part = date_val.split('T')[0] if 'T' in date_val else date_val.split(' ')[0]
                    exp_date = datetime.strptime(date_part, '%Y-%m-%d')
                else:
                    exp_date = datetime.fromisoformat(str(date_val))
                
                # Check if within range
                if start_date and exp_date < start_date:
                    continue
                if end_date and exp_date > end_date:
                    continue
                
                filtered.append(exp)
            except:
                continue
        
        return filtered
    
    def extract_time_period(self, query: str) -> tuple:
        """Extract time period from query and return (start_date, end_date, period_name)"""
        query_lower = query.lower()
        now = datetime.now()
        
        # This month
        if 'this month' in query_lower or 'current month' in query_lower:
            start = datetime(now.year, now.month, 1)
            return (start, now, 'this month')
        
        # Last month
        if 'last month' in query_lower or 'previous month' in query_lower:
            if now.month == 1:
                start = datetime(now.year - 1, 12, 1)
                end = datetime(now.year, 1, 1) - timedelta(days=1)
            else:
                start = datetime(now.year, now.month - 1, 1)
                end = datetime(now.year, now.month, 1) - timedelta(days=1)
            return (start, end, 'last month')
        
        # Specific month name
        for month_name, month_num in self.months.items():
            if month_name in query_lower:
                # Determine year
                year = now.year
                if month_num > now.month:
                    year = now.year - 1
                
                start = datetime(year, month_num, 1)
                if month_num == 12:
                    end = datetime(year + 1, 1, 1) - timedelta(days=1)
                else:
                    end = datetime(year, month_num + 1, 1) - timedelta(days=1)
                
                return (start, end, f"{month_name.title()} {year}")
        
        # This week
        if 'this week' in query_lower or 'current week' in query_lower:
            start = now - timedelta(days=now.weekday())
            return (start, now, 'this week')
        
        # Last week
        if 'last week' in query_lower or 'previous week' in query_lower:
            start = now - timedelta(days=now.weekday() + 7)
            end = now - timedelta(days=now.weekday() + 1)
            return (start, end, 'last week')
        
        # Today
        if 'today' in query_lower:
            start = datetime(now.year, now.month, now.day)
            return (start, now, 'today')
        
        # Yesterday
        if 'yesterday' in query_lower:
            yesterday = now - timedelta(days=1)
            start = datetime(yesterday.year, yesterday.month, yesterday.day)
            end = start + timedelta(days=1) - timedelta(seconds=1)
            return (start, end, 'yesterday')
        
        # Last N days
        days_match = re.search(r'last (\d+) days?', query_lower)
        if days_match:
            days = int(days_match.group(1))
            start = now - timedelta(days=days)
            return (start, now, f'last {days} days')
        
        return (None, None, None)
    
    def process_query(self, query: str, analysis: Dict[str, Any], context: str = "personal", expenses_data: List[Dict] = None) -> str:
        """Process natural language queries about expenses with advanced pattern matching"""
        query_lower = query.lower()
        
        # Extract time period if present
        start_date, end_date, period_name = self.extract_time_period(query_lower)
        
        # Filter expenses by date if time period detected
        if start_date and expenses_data:
            filtered_expenses = self.filter_by_date_range(expenses_data, start_date, end_date)
            
            if not filtered_expenses:
                return f"You haven't spent anything in {period_name}."
            
            # Re-analyze with filtered data
            analysis = self.analyze_expenses(filtered_expenses)
            expenses_data = filtered_expenses
            
            # Update context to include period
            time_context = f" in {period_name}"
        else:
            time_context = ""
        
        # Check for multiple categories in query (e.g., "food and grocery")
        matched_categories = []
        
        # Check actual categories from data first
        for actual_category in analysis['categories'].keys():
            if actual_category in query_lower:
                if actual_category not in matched_categories:
                    matched_categories.append(actual_category)
        
        # Check predefined category keywords
        for category, keywords in self.categories.items():
            cat_lower = category.lower()
            if cat_lower not in matched_categories:
                # Check if category name or any keyword is in query
                if cat_lower in query_lower or any(keyword in query_lower for keyword in keywords):
                    matched_categories.append(cat_lower)
        
        # Handle multiple categories
        if len(matched_categories) > 1:
            total_amount = 0
            total_count = 0
            category_details = []
            
            for cat in matched_categories:
                amount = analysis['categories'].get(cat, 0)
                if amount > 0:
                    count = len([exp for exp in expenses_data if exp.get('category', '').lower() == cat and exp.get('amount', 0) > 0])
                    total_amount += amount
                    total_count += count
                    category_details.append(f"{cat.title()}: Rs.{amount} ({count} txn)")
            
            if category_details:
                categories_str = " and ".join(matched_categories)
                details_str = ", ".join(category_details)
                return f"You've spent Rs.{total_amount} on {categories_str} across {total_count} transactions{time_context}. Breakdown: {details_str}."
        
        # Single category query
        if len(matched_categories) == 1:
            category = matched_categories[0]
            amount = analysis['categories'].get(category, 0)
            if amount > 0:
                cat_count = len([exp for exp in expenses_data if exp.get('category', '').lower() == category and exp.get('amount', 0) > 0])
                if cat_count > 1:
                    return f"You've spent Rs.{amount} on {category} across {cat_count} transactions{time_context}."
                else:
                    return f"You've spent Rs.{amount} on {category}{time_context}."
            else:
                if analysis['total'] > 0:
                    top_cat = analysis['top_categories'][0][0] if analysis['top_categories'] else 'other categories'
                    return f"You haven't spent anything on {category}{time_context}. Your main spending has been on {top_cat} (Rs.{analysis['top_categories'][0][1] if analysis['top_categories'] else 0})."
                else:
                    return f"You haven't spent anything on {category}{time_context}."
        
        # Income queries
        if any(word in query_lower for word in ['income', 'salary', 'earning', 'received', 'got']):
            if analysis.get('total_income', 0) > 0:
                return f"Your total income{time_context}: Rs.{analysis['total_income']} across {analysis['income_count']} transactions. Net balance: Rs.{analysis['net_balance']} ({'surplus' if analysis['net_balance'] >= 0 else 'deficit'})."
            else:
                return f"No income recorded{time_context}."
        
        # Total/Summary queries
        if any(word in query_lower for word in ['total', 'all', 'overall', 'everything', 'entire', 'whole']):
            income_summary = f" Income: Rs.{analysis.get('total_income', 0)} ({analysis.get('income_count', 0)} txn)." if analysis.get('total_income', 0) > 0 else ""
            if period_name:
                return f"You spent Rs.{analysis['total']} in {period_name} across {analysis['count']} transactions.{income_summary}"
            elif any(word in query_lower for word in ['till now', 'so far', 'upto now', 'up to now']):
                return f"You spent Rs.{analysis['total']} across {analysis['count']} transactions.{income_summary}"
            else:
                return f"You spent Rs.{analysis['total']} across {analysis['count']} transactions{time_context}.{income_summary}"
        
        # Specific item queries
        if expenses_data and any(word in query_lower for word in ['spend', 'spent', 'much', 'cost', 'price']):
            item_result = self.find_specific_item(query_lower, expenses_data)
            if item_result:
                item_name = item_result['item_name'].title()
                total = item_result['total_amount']
                count = item_result['count']
                
                if count == 1:
                    expense = item_result['expenses'][0]
                    date_info = f" on {expense.get('date', 'unknown date')}" if expense.get('date') else ""
                    paid_by = f" (paid by {expense.get('paid_by')})" if expense.get('paid_by') else ""
                    return f"You spent Rs.{total} on {item_name}{date_info}{paid_by}{time_context}."
                else:
                    return f"You spent Rs.{total} on {item_name} across {count} transactions{time_context}."
        
        # General spending queries
        if any(word in query_lower for word in ['spent', 'expense', 'much']):
            income_info = f" Income: Rs.{analysis.get('total_income', 0)}." if analysis.get('total_income', 0) > 0 else ""
            if period_name:
                return f"You spent Rs.{analysis['total']} in {period_name} across {analysis['count']} transactions.{income_info}"
            else:
                return f"You spent Rs.{analysis['total']} across {analysis['count']} transactions{time_context}.{income_info}"

        # Breakdown/Category analysis
        if any(word in query_lower for word in ['category', 'breakdown', 'categories', 'where', 'what']):
            if analysis['top_categories']:
                breakdown = []
                for cat, amount in analysis['top_categories']:
                    percentage = (amount / analysis['total'] * 100) if analysis['total'] > 0 else 0
                    breakdown.append(f"• {cat.title()}: Rs.{amount} ({percentage:.1f}%)")
                return f"Your {context} expense breakdown:\n" + "\n".join(breakdown)

        # Recent expenses
        if any(word in query_lower for word in ['recent', 'last', 'latest']):
            if analysis['recent_expenses']:
                recent = []
                for exp in analysis['recent_expenses'][:3]:
                    date_str = f" on {exp.get('date', 'unknown date')}" if exp.get('date') else ""
                    recent.append(f"• Rs.{exp.get('amount', 0)} on {exp.get('item', 'item')} ({exp.get('category', 'other')}){date_str}")
                return f"Your recent {context} expenses:\n" + "\n".join(recent)

        # Average/Daily spending
        if any(word in query_lower for word in ['average', 'daily', 'per day']):
            income_avg = analysis.get('total_income', 0) / analysis['days_tracked'] if analysis['days_tracked'] > 0 and analysis.get('total_income', 0) > 0 else 0
            income_info = f" Daily income average: Rs.{round(income_avg, 2)}." if income_avg > 0 else ""
            return f"Your average daily {context} spending is Rs.{analysis['average_per_day']} over {analysis['days_tracked']} days.{income_info}"

        # Comparison queries
        if 'most' in query_lower and ('spent' in query_lower or 'expensive' in query_lower):
            if analysis['top_categories']:
                top_cat, top_amount = analysis['top_categories'][0]
                return f"You've spent the most on {top_cat.title()} with Rs.{top_amount} in your {context} expenses."

        # Count queries
        if any(word in query_lower for word in ['how many', 'count', 'number']):
            income_info = f" and {analysis.get('income_count', 0)} income transactions (Rs.{analysis.get('total_income', 0)})" if analysis.get('total_income', 0) > 0 else ""
            return f"You have {analysis['count']} expense transactions totaling Rs.{analysis['total']}{income_info} in your {context} records."

        # Who paid queries
        if any(word in query_lower for word in ['who paid', 'who payed', 'paid by', 'payed by']):
            category_found = None
            for category in self.categories.keys():
                if category in query_lower:
                    category_found = category
                    break
            
            if category_found:
                category_expenses = [exp for exp in analysis['recent_expenses'] 
                                   if exp.get('category', '').lower() == category_found]
                if category_expenses:
                    recent_with_payer = [exp for exp in category_expenses if exp.get('paid_by')]
                    if recent_with_payer:
                        latest = recent_with_payer[0]
                        return f"The last {category_found} expense was Rs.{latest.get('amount', 0)} for {latest.get('item', 'item')} paid by {latest.get('paid_by', 'unknown')}."
                    else:
                        return f"I found recent {category_found} expenses but no payment information is recorded."
                else:
                    return f"No recent {category_found} expenses found."
            else:
                recent_with_payer = [exp for exp in analysis['recent_expenses'] if exp.get('paid_by')]
                if recent_with_payer:
                    latest = recent_with_payer[0]
                    return f"The most recent expense with payment info: Rs.{latest.get('amount', 0)} for {latest.get('item', 'item')} paid by {latest.get('paid_by', 'unknown')}."
                else:
                    return f"No recent expenses have payment information recorded."

        # Help/What can I ask queries
        if any(word in query_lower for word in ['help', 'what can', 'options']):
            return f"You can ask me about:\n• Total expenses ('What are my expenses till now?')\n• Income tracking ('What's my total income?')\n• Net balance ('What's my balance?')\n• Category breakdowns ('Show me my food expenses')\n• Recent transactions ('What are my recent expenses?')\n• Daily averages ('What's my daily spending?')\n• Comparisons ('What did I spend the most on?')\n• Who paid ('Who paid for grocery last time?')"

        # Balance/Net queries
        if any(word in query_lower for word in ['balance', 'net', 'left', 'remaining', 'save', 'saved']):
            if analysis.get('total_income', 0) > 0:
                return f"Your net balance{time_context}: Rs.{analysis['net_balance']} ({'surplus' if analysis['net_balance'] >= 0 else 'deficit'}). Income: Rs.{analysis['total_income']}, Expenses: Rs.{analysis['total']}."
            else:
                return f"No income data available to calculate balance. Total expenses: Rs.{analysis['total']}."
        
        # Default comprehensive response with better analysis
        if analysis['top_categories']:
            top_category, top_amount = analysis['top_categories'][0]
            percentage = (top_amount / analysis['total'] * 100) if analysis['total'] > 0 else 0
            income_info = f" Income: Rs.{analysis.get('total_income', 0)} ({analysis.get('income_count', 0)} txn)." if analysis.get('total_income', 0) > 0 else ""
            return f"You spent Rs.{analysis['total']}{time_context} across {analysis['count']} transactions. Top spending: {top_category.title()} (Rs.{top_amount}, {percentage:.1f}%).{income_info}"
        else:
            income_info = f" Income: Rs.{analysis.get('total_income', 0)} ({analysis.get('income_count', 0)} txn)." if analysis.get('total_income', 0) > 0 else ""
            return f"You spent Rs.{analysis['total']}{time_context} across {analysis['count']} transactions.{income_info}"