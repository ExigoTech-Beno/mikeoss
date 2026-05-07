"""
AustLII search plugin for Semantic Kernel.

Searches the Australasian Legal Information Institute database for:
- Australian case law (High Court, Federal Court, state courts)
- Commonwealth and state legislation
- Tribunal decisions (VCAT, NCAT, AAT, Fair Work Commission etc.)

AustLII search engine: SINO (sinosrch.cgi)
  Search:   GET /cgi-bin/sinosrch.cgi?query=...&mask_path=au&method=auto&view=relevance&results=10
  Document: GET /cgi-bin/viewdoc/au/cases/cth/HCA/2003/5.html
  Legis:    GET /cgi-bin/viewdb/au/legis/cth/consol_act/pa1988108/

No API key required for public search. A browser-like User-Agent is required
(AustLII blocks bare requests). Contact austlii.edu.au for bulk/commercial use.
"""

from __future__ import annotations
import json
import re
from typing import Annotated
import httpx

from semantic_kernel.functions import kernel_function
from app.config import settings

# Browser-like User-Agent required — AustLII returns 403 for bare requests
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
_HEADERS = {"User-Agent": _UA, "Accept": "text/html,application/xhtml+xml"}

AUSTLII_BASE = "https://www.austlii.edu.au"

# ---------------------------------------------------------------------------
# SINO mask_path registry  (source: austlii_reference.md + Zotero translator)
# ---------------------------------------------------------------------------
AUSTLII_DATABASES: dict[str, str] = {
    # ── Broad / all-jurisdiction ──────────────────────────────────────────
    "all":                      "au",
    "all_cases":                "au/cases",
    "all_cth_cases":            "au/cases/cth",
    "all_nsw_cases":            "au/cases/nsw",
    "all_vic_cases":            "au/cases/vic",
    "all_qld_cases":            "au/cases/qld",
    "all_wa_cases":             "au/cases/wa",
    "all_sa_cases":             "au/cases/sa",
    "all_tas_cases":            "au/cases/tas",
    "all_nt_cases":             "au/cases/nt",
    "all_act_cases":            "au/cases/act",
    # ── Commonwealth courts ───────────────────────────────────────────────
    "high_court":               "au/cases/cth/HCA",
    "federal_court":            "au/cases/cth/FCA",
    "full_federal_court":       "au/cases/cth/FCAFC",
    "fed_circuit_family_d1":    "au/cases/cth/FedCFamC1A",
    "fed_circuit_family_d2":    "au/cases/cth/FedCFamC2F",
    # ── Commonwealth tribunals ────────────────────────────────────────────
    "aat":                      "au/cases/cth/AAATA",
    "fair_work":                "au/cases/cth/FWC",
    "fair_work_full_bench":     "au/cases/cth/FWCFB",
    "oaic":                     "au/cases/cth/AICmr",   # Privacy / OAIC decisions
    "accc":                     "au/cases/cth/ACCC",
    "competition_tribunal":     "au/cases/cth/ACT",
    "copyright_tribunal":       "au/cases/cth/CopT",
    "nntt":                     "au/cases/cth/NNTT",    # National Native Title Tribunal
    # ── Commonwealth legislation ──────────────────────────────────────────
    "cth_legislation":          "au/legis/cth/consol_act",
    "cth_regulations":          "au/legis/cth/consol_reg",
    "cth_bills":                "au/legis/cth/bill",
    # ── ACT ───────────────────────────────────────────────────────────────
    "actsc":                    "au/cases/act/ACTSC",
    "actca":                    "au/cases/act/ACTCA",
    "acat":                     "au/cases/act/ACAT",
    "act_legislation":          "au/legis/act/consol_act",
    # ── NSW ───────────────────────────────────────────────────────────────
    "nswca":                    "au/cases/nsw/NSWCA",
    "nswcca":                   "au/cases/nsw/NSWCCA",
    "nswsc":                    "au/cases/nsw/NSWSC",
    "nswdc":                    "au/cases/nsw/NSWDC",
    "nswlec":                   "au/cases/nsw/NSWLEC",  # Land & Environment Court
    "nsw_irc":                  "au/cases/nsw/NSWIRComm",
    "ncat":                     "au/cases/nsw/NSWCATAP",
    "ncat_admin":               "au/cases/nsw/NSWCATAD",
    "ncat_consumer":            "au/cases/nsw/NSWCATCD",
    "nsw_legislation":          "au/legis/nsw/consol_act",
    # ── VIC ───────────────────────────────────────────────────────────────
    "vsca":                     "au/cases/vic/VSCA",
    "vsc":                      "au/cases/vic/VSC",
    "vcc":                      "au/cases/vic/VCC",
    "vcat":                     "au/cases/vic/VCAT",
    "vic_legislation":          "au/legis/vic/consol_act",
    # ── QLD ───────────────────────────────────────────────────────────────
    "qca":                      "au/cases/qld/QCA",
    "qsc":                      "au/cases/qld/QSC",
    "qdc":                      "au/cases/qld/QDC",
    "qcat":                     "au/cases/qld/QCAT",
    "qirc":                     "au/cases/qld/QIRC",
    "qpec":                     "au/cases/qld/QPEC",   # Planning & Environment Court
    "qld_legislation":          "au/legis/qld/consol_act",
    # ── WA ────────────────────────────────────────────────────────────────
    "wasca":                    "au/cases/wa/WASCA",
    "wasc":                     "au/cases/wa/WASC",
    "wadc":                     "au/cases/wa/WADC",
    "wasat":                    "au/cases/wa/WASAT",   # State Admin Tribunal
    "wa_irc":                   "au/cases/wa/WAIRComm",
    "wa_legislation":           "au/legis/wa/consol_act",
    # ── SA ────────────────────────────────────────────────────────────────
    "sascfc":                   "au/cases/sa/SASCFC",
    "sasc":                     "au/cases/sa/SASC",
    "sadc":                     "au/cases/sa/SADC",
    "sacat":                    "au/cases/sa/SACAT",
    "saet":                     "au/cases/sa/SAET",    # Employment Tribunal
    "sa_legislation":           "au/legis/sa/consol_act",
    # ── TAS ───────────────────────────────────────────────────────────────
    "tassc":                    "au/cases/tas/TASSC",
    "tascca":                   "au/cases/tas/TASCCA",
    "tascat":                   "au/cases/tas/TASCAT",
    "tas_legislation":          "au/legis/tas/consol_act",
    # ── NT ────────────────────────────────────────────────────────────────
    "ntsc":                     "au/cases/nt/NTSC",
    "ntcca":                    "au/cases/nt/NTCCA",
    "ntcat":                    "au/cases/nt/NTCAT",
    "nt_legislation":           "au/legis/nt/consol_act",
    # ── Journals & Treaties ───────────────────────────────────────────────
    "journals":                 "au/journals",
    "treaties":                 "au/other/dfat",
}

# ---------------------------------------------------------------------------
# Known Acts — AustLII consol_act identifiers
# Use with browse_legislation: path = f"/au/legis/cth/consol_act/{KNOWN_ACTS[name]}"
# ---------------------------------------------------------------------------
KNOWN_ACTS: dict[str, str] = {
    "Privacy Act 1988":                     "pa1988108",
    "Corporations Act 2001":                "ca2001172",
    "Fair Work Act 2009":                   "fwa2009114",
    "Competition and Consumer Act 2010":    "caca2010265",   # Schedule 2 = ACL
    "Evidence Act 1995":                    "ea199580",
    "Criminal Code Act 1995":               "cca1995115",
    "Income Tax Assessment Act 1997":       "itaa1997240",
    "Freedom of Information Act 1982":      "foia1982222",
    "National Consumer Credit Protection Act 2009": "nccpa2009277",
    "Family Law Act 1975":                  "fla1975278",
    "Bankruptcy Act 1966":                  "ba1966142",
    "Migration Act 1958":                   "ma1958069",
    "Native Title Act 1993":                "nta1993147",
    "Racial Discrimination Act 1975":       "rda1975040",
    "Sex Discrimination Act 1984":          "sda1984209",
    "Disability Discrimination Act 1992":   "dda1992264",
    "Age Discrimination Act 2004":          "ada2004292",
    "Australian Human Rights Commission Act 1986": "ahrca1986163",
    "Work Health and Safety Act 2011":      "whasa2011121",
    "Superannuation (Industry) Act 1993":   "sia1993473",
}


class AustLIIPlugin:
    """Search Australian legal databases via AustLII SINO search engine."""

    @kernel_function(
        name="search_austlii",
        description=(
            "Search AustLII for Australian case law, legislation, and tribunal decisions. "
            "Use this for questions about Australian law, legal precedents, statutory "
            "interpretation, or privacy/employment/contract/corporate law cases. "
            "Returns titles, citations, and URLs. Follow with get_austlii_document to read full text. "
            "Database keys include: all, high_court, federal_court, full_federal_court, "
            "aat, fair_work, fair_work_full_bench, oaic (privacy decisions), accc, nntt, "
            "cth_legislation, nswca, nswsc, nswdc, nswlec, ncat, ncat_admin, ncat_consumer, "
            "vsca, vsc, vcat, qca, qsc, qcat, wasca, wasc, wasat, sascfc, sasc, sacat, "
            "tassc, ntsc, acat, journals, treaties, and all_*_cases jurisdiction-wide masks."
        ),
    )
    async def search_austlii(
        self,
        query: Annotated[
            str,
            "Legal search query using boolean operators if needed. "
            "Examples: 'misleading conduct ACL s18', 'unfair dismissal reasonable notice', "
            "'privacy breach APP 11', 'directors duty s181 Corporations Act'",
        ],
        database: Annotated[
            str,
            "Database key from: all, high_court, federal_court, full_federal_court, "
            "aat, fair_work, oaic, cth_legislation, nswca, nswsc, ncat, nsw_legislation, "
            "vsca, vcat, vic_legislation, qca, qld_legislation, wasca, wa_legislation",
        ] = "all",
        sort_by: Annotated[str, "Sort results by 'relevance' or 'date'"] = "relevance",
        max_results: Annotated[int, "Number of results to return (1–20)"] = 10,
    ) -> str:
        mask = AUSTLII_DATABASES.get(database, "au")
        params = {
            "query": query,
            "mask_path": mask,
            "method": "auto",
            "view": sort_by if sort_by in ("relevance", "date") else "relevance",
            "results": str(min(max_results, 20)),
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(
                    f"{AUSTLII_BASE}/cgi-bin/sinosrch.cgi",
                    params=params,
                    headers=_HEADERS,
                    follow_redirects=True,
                )
            if resp.status_code == 200:
                return _parse_sino_results(resp.text, query, mask)
            return json.dumps({
                "error": f"AustLII HTTP {resp.status_code}",
                "fallback": f"Search manually: https://www.austlii.edu.au/cgi-bin/sinosrch.cgi?query={query}&mask_path={mask}",
            })
        except Exception as exc:
            return json.dumps({"error": str(exc), "query": query})

    @kernel_function(
        name="get_austlii_document",
        description=(
            "Retrieve the full text of a specific AustLII case, legislation section, or "
            "tribunal decision. Provide the path from a search result, e.g. "
            "'/au/cases/cth/HCA/2003/5.html' or '/au/legis/cth/consol_act/pa1988108/s14.html'. "
            "Returns plain text of the judgment or provision."
        ),
    )
    async def get_document(
        self,
        path: Annotated[
            str,
            "AustLII document path starting with /au/. "
            "Cases: /au/cases/cth/HCA/2003/5.html  "
            "Legislation section: /au/legis/cth/consol_act/pa1988108/s13.html",
        ],
    ) -> str:
        # viewdoc for cases/journals, viewdb for legislation tables of contents
        if "/legis/" in path and not path.endswith(".html"):
            endpoint = f"{AUSTLII_BASE}/cgi-bin/viewdb{path}"
        else:
            endpoint = f"{AUSTLII_BASE}/cgi-bin/viewdoc{path}"
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.get(endpoint, headers=_HEADERS, follow_redirects=True)
            if resp.status_code != 200:
                return json.dumps({"error": f"HTTP {resp.status_code}", "url": endpoint})
            text = _strip_html(resp.text)
            if len(text) > 16000:
                text = text[:16000] + "\n\n[Truncated — request a specific section or paragraph range]"
            return json.dumps({"path": path, "url": endpoint, "text": text})
        except Exception as exc:
            return json.dumps({"error": str(exc), "path": path})

    @kernel_function(
        name="lookup_act",
        description=(
            "Look up a known Commonwealth Act on AustLII by name and return its table of contents. "
            "Knows: Privacy Act 1988, Corporations Act 2001, Fair Work Act 2009, "
            "Competition and Consumer Act 2010, Evidence Act 1995, Criminal Code Act 1995, "
            "Freedom of Information Act 1982, Family Law Act 1975, Migration Act 1958, "
            "Racial Discrimination Act 1975, Sex Discrimination Act 1984, "
            "Disability Discrimination Act 1992, Age Discrimination Act 2004, "
            "Work Health and Safety Act 2011, and more."
        ),
    )
    async def lookup_act(
        self,
        act_name: Annotated[
            str,
            "Exact or partial name of the Act, e.g. 'Privacy Act 1988', 'Fair Work Act 2009', "
            "'Corporations Act'. Case-insensitive partial match is supported.",
        ],
    ) -> str:
        # Find best match (case-insensitive partial)
        name_lower = act_name.lower()
        match = next(
            (
                (name, ident)
                for name, ident in KNOWN_ACTS.items()
                if name_lower in name.lower() or name.lower() in name_lower
            ),
            None,
        )
        if not match:
            available = list(KNOWN_ACTS.keys())
            return json.dumps({
                "error": f"Act '{act_name}' not in known registry.",
                "available": available,
                "tip": "Use browse_legislation with the full AustLII path, or search_austlii.",
            })
        full_name, ident = match
        act_path = f"/au/legis/cth/consol_act/{ident}"
        sections = await self.browse_legislation(act_path)
        result = json.loads(sections)
        result["act_name"] = full_name
        result["identifier"] = ident
        return json.dumps(result)
        description=(
            "List the sections of a Commonwealth or state Act on AustLII. "
            "Provide the Act's AustLII path, e.g. '/au/legis/cth/consol_act/pa1988108' "
            "for the Privacy Act 1988. Returns a table of contents with section links."
        ),
    )
    async def browse_legislation(
        self,
        act_path: Annotated[
            str,
            "AustLII legislation path without trailing slash. "
            "Privacy Act 1988: /au/legis/cth/consol_act/pa1988108  "
            "Corporations Act 2001: /au/legis/cth/consol_act/ca2001172  "
            "Fair Work Act 2009: /au/legis/cth/consol_act/fwa2009114",
        ],
    ) -> str:
        url = f"{AUSTLII_BASE}/cgi-bin/viewdb{act_path}/"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.get(url, headers=_HEADERS, follow_redirects=True)
            if resp.status_code != 200:
                return json.dumps({"error": f"HTTP {resp.status_code}", "url": url})
            sections = _parse_toc(resp.text, act_path)
            return json.dumps({"act_path": act_path, "url": url, "sections": sections})
        except Exception as exc:
            return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# HTML parsing helpers
# ---------------------------------------------------------------------------

def _parse_sino_results(html: str, query: str, mask: str) -> str:
    """Parse sinosrch.cgi HTML response into structured results."""
    results: list[dict] = []

    # sinosrch result links: <a href="/cgi-bin/viewdoc/au/..."> or <a href="/au/...">
    patterns = [
        re.compile(r'href="(/cgi-bin/viewdoc/au/[^"]+\.html)"[^>]*>\s*([^<]{5,})</a>', re.I),
        re.compile(r'href="(/au/[^"]+\.html)"[^>]*>\s*([^<]{5,})</a>', re.I),
    ]

    seen: set[str] = set()
    for pattern in patterns:
        for m in pattern.finditer(html):
            raw_path, title = m.group(1), m.group(2).strip()
            # Normalise: strip /cgi-bin/viewdoc prefix if present
            path = raw_path.replace("/cgi-bin/viewdoc", "")
            if path in seen:
                continue
            seen.add(path)
            results.append({
                "title": title,
                "path": path,
                "url": f"{AUSTLII_BASE}/cgi-bin/viewdoc{path}",
            })
            if len(results) >= 20:
                break
        if len(results) >= 20:
            break

    if not results:
        return json.dumps({
            "query": query,
            "database": mask,
            "results": [],
            "note": "No results. Try broader terms or check database key.",
            "manual_search": f"https://www.austlii.edu.au/cgi-bin/sinosrch.cgi?query={query}&mask_path={mask}",
        })

    return json.dumps({
        "query": query,
        "database": mask,
        "count": len(results),
        "results": results,
        "source": "AustLII",
    })


def _parse_toc(html: str, act_path: str) -> list[dict]:
    """Extract section links from a legislation table of contents page."""
    sections: list[dict] = []
    pattern = re.compile(
        rf'href="(/cgi-bin/viewdoc{re.escape(act_path)}/s[^"]+\.html)"[^>]*>\s*([^<]+)</a>',
        re.I,
    )
    for m in pattern.finditer(html):
        raw_path, label = m.group(1), m.group(2).strip()
        path = raw_path.replace("/cgi-bin/viewdoc", "")
        sections.append({"section": label, "path": path})
    return sections[:100]  # cap at 100 sections


def _strip_html(html: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&#\d+;", " ", text)
    text = re.sub(r"\s{3,}", "\n\n", text)
    return text.strip()
