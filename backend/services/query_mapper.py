
import re
from typing import List, Optional, Tuple

# Mapping of keywords/phrases to Graph Node IDs
NODE_MAPPINGS = {
    "Income Tax": {
        "form 16": "Form16", "salary certificate": "Form16", "tds": "Form16",
        "26as": "Form26AS", "tax credit": "Form26AS",
        "ais": "AIS", "annual info": "AIS",
        "file": "ITR_Filing", "filing": "ITR_Filing", "itr": "ITR_Filing",
        "itr 1": "ITR1", "itr 2": "ITR2", "itr 3": "ITR3", "itr 4": "ITR4", "itr 5": "ITR5", "itr 6": "ITR6", "itr 7": "ITR7",
        "itr-1": "ITR1", "itr-2": "ITR2", "itr-3": "ITR3", "itr-4": "ITR4", "itr-5": "ITR5", "itr-6": "ITR6", "itr-7": "ITR7",
        "verify": "Verification", "verification": "Verification", "itr-v": "Verification",
        "processing": "Processing", "cpc": "Processing",
        "139(9)": "Notice_139_9", "defective": "Defective_Return",
        "correction": "Correction", "rectification": "Correction",
        "refund": "Refund", "delayed refund": "Refund", "tax refund": "Refund",
        "demand": "Demand", "tax due": "Demand",
        "audit": "Tax_Audit", "3ca": "Form3CA", "3cb": "Form3CB", "3cd": "Form3CD", "3ceb": "Form3CEB",
        "dsc": "DSC_Tutorial", "digital signature": "DSC_Tutorial"
    },
    "EPFO": {
        "uan": "UAN", "universal account": "UAN",
        "kyc": "KYC", "aadhaar link": "KYC", "pan link": "KYC",
        "claim": "PF_Claim", "withdraw": "PF_Claim", "withdrawal": "PF_Claim", "application": "PF_Claim",
        "form 19": "Form19", "settlement": "Form19",
        "form 31": "Form31", "advance": "Form31",
        "form 10c": "Form10C", "pension": "Form10C",
        "form 1": "EPF_Form1", "form 2": "EPF_Form2", "nomination": "EPF_Form2",
        "form 5": "EPF_Form5", "form 11": "EPF_Form11", "declaration": "EPF_Form11",
        "form 13": "EPF_Form13", "transfer": "Bank_Transfer",
        "form 14": "EPF_Form14", "lic": "LIC_PF_Payment", "policy": "LIC_PF_Payment",
        "form 20": "EPF_Form20", "death claim": "EPF_Form20",
        "employer": "Employer_Verification",
        "approval": "Field_Office_Approval", "epfo office": "Field_Office_Approval",
        "transfer": "Bank_Transfer", "credit": "Bank_Transfer",
        "contribution": "Contribution_Statement", "annual statement": "Contribution_Statement"
    },
    "Passport": {
        "apply": "Application",
        "passport application": "Application",
        "appointment": "Appointment",
        "psk": "Appointment",
        "verify documents": "Document_Verification",
        "granting": "Document_Verification",
        "police": "Police_Verification",
        "printing": "Passport_Printing",
        "dispatch": "Dispatch",
        "speed post": "Dispatch",
        "delivery": "Delivery"
    }
}

def map_query_to_graph_nodes(query_text: str) -> List[Tuple[str, str]]:
    query_lower = query_text.lower()
    detected_nodes = []
    
    for domain, mappings in NODE_MAPPINGS.items():
        for keyword, node_id in mappings.items():
            if keyword in query_lower:
                # Store as (domain, node_id)
                detected_nodes.append((domain, node_id))
    
    return list(set(detected_nodes)) # Unique pairs
