"""
Australian legislation plugin for Semantic Kernel.

Sources:
- legislation.gov.au (Federal Register of Legislation) — official Commonwealth Acts
- Australian Privacy Principles (embedded from Privacy Act 1988, Schedule 1)
- ATO legal database (public)

The Australian Privacy Principles (APPs) are embedded in full as a knowledge
base so they are always available without any API call — critical for any
legal AI tool operating in Australia.
"""

from __future__ import annotations
import json
from typing import Annotated
import httpx

from semantic_kernel.functions import kernel_function


# ---------------------------------------------------------------------------
# Australian Privacy Principles — embedded knowledge base
# Source: Privacy Act 1988 (Cth), Schedule 1, as amended by Privacy
# Amendment (Enhancing Privacy Protection) Act 2012 and subsequent amendments.
# Current as at 2024.
# ---------------------------------------------------------------------------

AUSTRALIAN_PRIVACY_PRINCIPLES = {
    "overview": (
        "The Australian Privacy Principles (APPs) are contained in Schedule 1 of the "
        "Privacy Act 1988 (Cth). They apply to APP entities: Australian Government agencies "
        "and private sector organisations with annual turnover > $3 million (with some exceptions). "
        "Breaches can attract civil penalties up to $50 million for serious or repeated breaches "
        "under the Privacy and Other Legislation Amendment Act 2024."
    ),
    "principles": [
        {
            "number": 1,
            "title": "Open and transparent management of personal information",
            "summary": "APP entities must manage personal information in an open and transparent way, including maintaining an up-to-date privacy policy that is freely available.",
            "key_obligations": [
                "Have a clearly expressed, up-to-date APP privacy policy",
                "Make the privacy policy available free of charge (usually on website)",
                "Privacy policy must cover: what information is collected, why, how it is held, how to access/correct it, how to complain",
            ],
            "section": "APP 1.1–1.5",
        },
        {
            "number": 2,
            "title": "Anonymity and pseudonymity",
            "summary": "Individuals must have the option of not identifying themselves or using a pseudonym when dealing with APP entities, unless identification is required by law or impracticable.",
            "key_obligations": [
                "Offer anonymity or pseudonymity where lawful and practicable",
                "Exceptions: if law requires identification, or identification is necessary for the entity's functions",
            ],
            "section": "APP 2.1–2.2",
        },
        {
            "number": 3,
            "title": "Collection of solicited personal information",
            "summary": "Limits collection of personal information to what is reasonably necessary. Higher standard for sensitive information (requires consent or legal basis).",
            "key_obligations": [
                "Only collect if reasonably necessary for entity's functions or activities",
                "Sensitive information: only with consent or under specific exceptions (health, legal proceedings, etc.)",
                "Must collect by lawful and fair means",
                "Collect directly from the individual where reasonable and practicable",
            ],
            "section": "APP 3.1–3.6",
            "note": "Sensitive information includes: health, racial/ethnic origin, political opinions, religious beliefs, sexual orientation, biometric data, criminal record.",
        },
        {
            "number": 4,
            "title": "Dealing with unsolicited personal information",
            "summary": "If an entity receives personal information it did not solicit, it must determine whether it could have collected it under APP 3. If not, must destroy or de-identify it.",
            "key_obligations": [
                "Assess whether the unsolicited information could have been collected under APP 3",
                "If not: destroy or de-identify as soon as practicable",
                "If yes: treat as if solicited (APPs apply)",
            ],
            "section": "APP 4.1–4.5",
        },
        {
            "number": 5,
            "title": "Notification of the collection of personal information",
            "summary": "At or before the time of collection, APP entities must take reasonable steps to notify individuals of key matters.",
            "key_obligations": [
                "Notify: entity's identity and contact details",
                "Notify: purposes for collection",
                "Notify: main consequences of not providing information",
                "Notify: how to access and correct the information",
                "Notify: whether information will be disclosed overseas and to which countries",
            ],
            "section": "APP 5.1–5.2",
        },
        {
            "number": 6,
            "title": "Use or disclosure of personal information",
            "summary": "Personal information can only be used or disclosed for the primary purpose of collection, or a secondary purpose if an exception applies.",
            "key_obligations": [
                "Primary purpose rule: use/disclose only for the purpose it was collected",
                "Secondary purpose exceptions: individual has consented; they would reasonably expect it; directly related to primary purpose (for sensitive info: directly related only)",
                "Other exceptions: required by law, enforcement body functions, health/safety",
            ],
            "section": "APP 6.1–6.4",
        },
        {
            "number": 7,
            "title": "Direct marketing",
            "summary": "Organisations (not government agencies) may only use or disclose personal information for direct marketing if specific conditions are met.",
            "key_obligations": [
                "Must provide a simple opt-out mechanism",
                "Must not use sensitive information for direct marketing without consent",
                "If information collected from third party: must have consent or it must be impracticable to obtain",
                "Must honour opt-out requests promptly",
            ],
            "section": "APP 7.1–7.7",
        },
        {
            "number": 8,
            "title": "Cross-border disclosure of personal information",
            "summary": "Before disclosing personal information overseas, the entity must take reasonable steps to ensure the overseas recipient complies with the APPs.",
            "key_obligations": [
                "Take reasonable steps to ensure overseas recipient complies with APPs",
                "Entity remains accountable for overseas recipient's handling",
                "Exception: individual has consented after being informed of the risks",
                "Exception: disclosure required or authorised by law",
            ],
            "section": "APP 8.1–8.2",
            "note": "This is critical for cloud services — storing data with US/EU providers means APP 8 applies. Using Australian Azure region avoids this issue.",
        },
        {
            "number": 9,
            "title": "Adoption, use or disclosure of government related identifiers",
            "summary": "Organisations must not adopt a government identifier (e.g. Tax File Number, Medicare number) as their own identifier, except in limited circumstances.",
            "key_obligations": [
                "Do not adopt TFN, Medicare number, etc. as own identifier",
                "Do not use or disclose such identifiers except where necessary for the purpose they were collected",
                "Exceptions: required by law, identity verification by authorised agency",
            ],
            "section": "APP 9.1–9.5",
        },
        {
            "number": 10,
            "title": "Quality of personal information",
            "summary": "APP entities must take reasonable steps to ensure personal information is accurate, up to date, complete and relevant.",
            "key_obligations": [
                "At collection: ensure information is accurate, up to date, complete",
                "At use/disclosure: ensure information is also relevant to the purpose",
                "Implement processes to update records when individuals provide corrections",
            ],
            "section": "APP 10.1–10.2",
        },
        {
            "number": 11,
            "title": "Security of personal information",
            "summary": "APP entities must protect personal information from misuse, interference, loss, unauthorised access, modification or disclosure.",
            "key_obligations": [
                "Take reasonable steps to protect information: technical and organisational measures",
                "Destroy or de-identify information that is no longer needed (and not required by law to retain)",
                "Notifiable Data Breaches (NDB) scheme: must notify OAIC and affected individuals of eligible data breaches",
            ],
            "section": "APP 11.1–11.2",
            "note": "The Notifiable Data Breaches (NDB) scheme under Part IIIC requires notification to OAIC within 30 days of becoming aware of an eligible data breach.",
        },
        {
            "number": 12,
            "title": "Access to personal information",
            "summary": "Individuals have the right to access personal information held about them. APP entities must provide access on request unless an exception applies.",
            "key_obligations": [
                "Provide access within 30 days of request (or reasonable period)",
                "Cannot charge for making a request",
                "Can charge reasonable fee for giving access (not for health information held by health provider)",
                "Exceptions: unreasonable impact on others' privacy, prejudice enforcement activities, legal professional privilege, etc.",
                "If access refused: must provide reasons and advise of complaint mechanism",
            ],
            "section": "APP 12.1–12.10",
        },
        {
            "number": 13,
            "title": "Correction of personal information",
            "summary": "APP entities must take reasonable steps to correct personal information that is inaccurate, out of date, incomplete, irrelevant or misleading.",
            "key_obligations": [
                "Correct on own initiative or on request",
                "If correction requested: take reasonable steps within 30 days",
                "If correction refused: provide reasons and advise of complaint mechanism",
                "If corrected: notify third parties that received the incorrect information (if reasonable and practicable)",
            ],
            "section": "APP 13.1–13.5",
        },
    ],
    "penalties": {
        "civil": "Up to $50 million (body corporate) or $2.5 million (individual) for serious or repeated interferences with privacy — Privacy and Other Legislation Amendment Act 2024",
        "criminal": "Criminal penalties apply for doxxing (malicious re-identification) under 2024 amendments",
        "regulator": "Office of the Australian Information Commissioner (OAIC)",
        "complaint_process": "Complaint to OAIC → conciliation/investigation → determination → Federal Court (if needed)",
    },
    "source": "Privacy Act 1988 (Cth), Schedule 1; OAIC Guidelines; Privacy and Other Legislation Amendment Act 2024",
    "source_url": "https://www.oaic.gov.au/privacy/australian-privacy-principles",
}


class AustralianLegislationPlugin:
    """Tools for accessing Australian legislation and legal principles."""

    @kernel_function(
        name="get_australian_privacy_principles",
        description=(
            "Get the Australian Privacy Principles (APPs) under the Privacy Act 1988 (Cth). "
            "Use for any question about Australian privacy law, data handling obligations, "
            "data breach notification, cross-border data transfers, or APP compliance."
        ),
    )
    async def get_privacy_principles(
        self,
        principle_number: Annotated[int, "Specific APP number (1-13), or 0 for all principles"] = 0,
    ) -> str:
        if principle_number == 0:
            return json.dumps(AUSTRALIAN_PRIVACY_PRINCIPLES, indent=2)
        principles = AUSTRALIAN_PRIVACY_PRINCIPLES["principles"]
        match = next((p for p in principles if p["number"] == principle_number), None)
        if not match:
            return json.dumps({"error": f"APP {principle_number} not found. Valid range: 1–13"})
        return json.dumps({
            "overview": AUSTRALIAN_PRIVACY_PRINCIPLES["overview"],
            "principle": match,
            "penalties": AUSTRALIAN_PRIVACY_PRINCIPLES["penalties"],
            "source": AUSTRALIAN_PRIVACY_PRINCIPLES["source"],
        }, indent=2)

    @kernel_function(
        name="search_federal_legislation",
        description=(
            "Search the Federal Register of Legislation (legislation.gov.au) for Commonwealth Acts, "
            "regulations, and legislative instruments. Use for questions about current Australian federal law."
        ),
    )
    async def search_federal_legislation(
        self,
        query: Annotated[str, "Search terms, e.g. 'Privacy Act' or 'Corporations Act 2001'"],
        max_results: Annotated[int, "Maximum results to return"] = 10,
    ) -> str:
        try:
            # Federal Register of Legislation search API
            url = "https://legislation.gov.au/api/Search/List"
            params = {
                "searchTerm": query,
                "pageSize": min(max_results, 20),
                "pageNumber": 1,
                "status": "InForce",
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for item in data.get("results", [])[:max_results]:
                        results.append({
                            "title": item.get("title", ""),
                            "series_id": item.get("seriesId", ""),
                            "register_id": item.get("registerId", ""),
                            "type": item.get("legislationType", ""),
                            "status": item.get("status", ""),
                            "url": f"https://legislation.gov.au/Details/{item.get('registerId', '')}",
                        })
                    return json.dumps({"query": query, "results": results, "source": "legislation.gov.au"})
                else:
                    return json.dumps({
                        "error": f"legislation.gov.au returned {resp.status_code}",
                        "suggestion": f"Search manually at https://legislation.gov.au/Search/AdvancedSearch?SearchTerm={query.replace(' ', '+')}",
                    })
        except Exception as e:
            return json.dumps({"error": str(e)})

    @kernel_function(
        name="get_legislation_text",
        description="Retrieve the current text of a specific Commonwealth Act by its register ID from legislation.gov.au.",
    )
    async def get_legislation_text(
        self,
        register_id: Annotated[str, "The legislation register ID, e.g. 'C2024C00206' for the Privacy Act"],
        section: Annotated[str, "Specific section or schedule to retrieve, e.g. 'Schedule 1' or 's6'"] = "",
    ) -> str:
        try:
            url = f"https://legislation.gov.au/Details/{register_id}/Download/Serialised"
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code == 200:
                    text = resp.text
                    if section:
                        # Try to find the requested section
                        idx = text.lower().find(section.lower())
                        if idx >= 0:
                            text = text[idx:idx + 8000]
                        else:
                            text = text[:8000] + f"\n\n[Section '{section}' not found in first 8000 chars]"
                    elif len(text) > 10000:
                        text = text[:10000] + "\n\n[Content truncated — specify a section for more detail]"
                    return json.dumps({"register_id": register_id, "section": section, "text": text})
                return json.dumps({"error": f"HTTP {resp.status_code}", "register_id": register_id})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @kernel_function(
        name="check_app_compliance",
        description=(
            "Analyse a described data handling practice against the Australian Privacy Principles "
            "and identify which APPs are engaged and whether there are compliance risks."
        ),
    )
    async def check_app_compliance(
        self,
        practice: Annotated[str, "Description of the data handling practice to analyse, e.g. 'We collect client email addresses and share them with our US-based marketing platform'"],
    ) -> str:
        # Return the full APPs for the LLM to reason against
        return json.dumps({
            "instruction": (
                "Analyse the described practice against each of the 13 Australian Privacy Principles below. "
                "Identify which APPs are engaged, what obligations apply, and any compliance risks."
            ),
            "practice": practice,
            "australian_privacy_principles": AUSTRALIAN_PRIVACY_PRINCIPLES,
        }, indent=2)
