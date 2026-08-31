import re
from typing import Dict, Any

class IntentEngine:
    def extract_intent(self, prompt: str) -> Dict[str, Any]:
        prompt_lower = prompt.lower()
        
        intent = "UNKNOWN"
        action = "read"
        amount = 0.0
        customer_id = None
        resource = "general_system"
        
        if "refund" in prompt_lower:
            intent = "REFUND"
            action = "refund:create"
            resource = "refund_api"
            
            amounts = re.findall(r'[₹\$]?\s*([0-9,]+(?:\.[0-9]+)?)', prompt)
            if amounts:
                clean_amt = amounts[0].replace(',', '')
                try:
                    amount = float(clean_amt)
                except ValueError:
                    amount = 0.0
            
            cust_matches = re.findall(r'customer\s*#?([a-zA-Z0-9_-]+)', prompt_lower)
            if cust_matches:
                customer_id = cust_matches[0]

        elif "transfer" in prompt_lower or "pay" in prompt_lower:
            intent = "PAYMENT"
            action = "payment:execute"
            resource = "payment_gateway"
            amounts = re.findall(r'[₹\$]?\s*([0-9,]+(?:\.[0-9]+)?)', prompt)
            if amounts:
                try:
                    amount = float(amounts[0].replace(',', ''))
                except ValueError:
                    amount = 0.0
        
        elif "delete" in prompt_lower or "drop" in prompt_lower:
            intent = "DATA_DELETION"
            action = "database:delete"
            resource = "customer_db"
        
        elif "export" in prompt_lower or "download" in prompt_lower:
            intent = "DATA_EXPORT"
            action = "data:export"
            resource = "sensitive_records"

        return {
            "intent": intent,
            "action": action,
            "resource": resource,
            "amount": amount,
            "customer_id": customer_id,
            "raw_prompt": prompt
        }

intent_engine = IntentEngine()
