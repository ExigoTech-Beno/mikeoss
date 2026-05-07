"""
Built-in workflow definitions — ported from backend/src/lib/builtinWorkflows.ts.
These are Semantic Kernel prompt templates triggered by the workflows routes.
"""

BUILTIN_WORKFLOWS = [
    {
        "id": "builtin-cp-checklist",
        "title": "Generate CP Checklist",
        "prompt_md": """## Generate Conditions Precedent Checklist

Review the uploaded credit agreement or financing document and generate a comprehensive
Conditions Precedent (CP) checklist as a downloadable Word document in landscape orientation.

Structure the document with sections per category (Corporate, Financial, Legal, Security).
Each section has a table with four columns: Index, Clause Number, Clause, Status (leave blank).
Every table must have exactly these four columns in this order. The Index must be sequential
starting from 1 within each category.""",
    },
    {
        "id": "builtin-credit-summary",
        "title": "Credit Agreement Summary",
        "prompt_md": """## Credit Agreement Summary

Review the uploaded credit agreement and produce a comprehensive legal summary covering:
Lenders, Borrowers, Guarantors, Other Parties, Date, Facilities, Amount, Purpose, Interest,
Commitment Fee, Repayment Schedule, Maturity, Security, Guarantees, Financial Covenants,
Events of Default, Assignment, Change of Control, Prepayment Fee, Governing Law, Dispute Resolution.

For each section: identify key provisions, quote relevant clause references, and flag any
unusual, onerous, or non-market terms. Deliver inline in chat.""",
    },
    {
        "id": "builtin-due-diligence",
        "title": "Due Diligence Summary",
        "prompt_md": """## Due Diligence Summary

Review the uploaded documents and produce a structured due diligence summary.
Identify key risks, unusual provisions, missing standard protections, and items
requiring further investigation. Organise by category: Corporate, Commercial,
Financial, Legal/Regulatory, IP, Employment, Property.""",
    },
]
