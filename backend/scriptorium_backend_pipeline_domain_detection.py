"""
Domain Detection Layer
Lightweight keyword + pattern classifier that routes documents
to domain-specific processing handlers.
"""

import re
from typing import Tuple, Dict, List
from collections import Counter
from loguru import logger

from models.schemas import Domain


# ─── Domain Vocabulary ────────────────────────────────────────────────────────

DOMAIN_SIGNALS: Dict[str, Dict] = {
    Domain.CHEMISTRY: {
        "keywords": [
            "reaction", "catalyst", "synthesis", "compound", "molecule", "reagent",
            "yield", "solvent", "oxidation", "reduction", "polymer", "isotope",
            "spectroscopy", "nmr", "hplc", "chromatography", "titration", "molarity",
            "enthalpy", "gibbs", "kinetics", "stoichiometry", "orbital", "bond",
            "electron", "proton", "alkane", "alkene", "aromatic", "ester",
            "aldehyde", "ketone", "carboxylic", "amino acid", "enzyme", "substrate",
            "ph", "buffer", "precipitation", "crystallization", "distillation",
            "electrode", "electrolyte", "galvanic", "ionization", "sublimation",
        ],
        "patterns": [
            r"\b[A-Z][a-z]?\d*(\([+-]?\d*\))?\b",  # chemical formulas
            r"\b\d+\s*%\s*yield\b",                  # yield percentages
            r"\b\d+\s*°[CF]\b",                      # temperatures
            r"\b\d+\s*mol[/\s]",                     # molar quantities
            r"\bpH\s*\d",                            # pH values
        ],
        "weight": 1.2,
    },
    Domain.FINANCE: {
        "keywords": [
            "revenue", "ebitda", "margin", "profit", "loss", "equity", "debt",
            "assets", "liabilities", "cashflow", "valuation", "ipo", "merger",
            "acquisition", "dividend", "eps", "pe ratio", "wacc", "dcf", "irr",
            "npv", "cagr", "basis points", "leverage", "roi", "roa", "roe",
            "balance sheet", "income statement", "quarterly", "fiscal", "guidance",
            "underwrite", "amortization", "depreciation", "capex", "opex",
            "hedge", "derivative", "arbitrage", "portfolio", "benchmark",
            "alpha", "beta", "volatility", "liquidity", "solvency",
        ],
        "patterns": [
            r"\$\s*[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|trillion|mn|bn))?",
            r"\b[\d,]+(?:\.\d+)?\s*(?:million|billion|trillion|mn|bn)\b",
            r"\b\d+(?:\.\d+)?[xX]\b",               # multiples
            r"\b\d+(?:\.\d+)?%\b",                   # percentages
            r"\bQ[1-4]\s*\'\d{2}\b",                 # quarters
            r"\bFY\s*\d{4}\b",                       # fiscal years
        ],
        "weight": 1.1,
    },
    Domain.LAW: {
        "keywords": [
            "plaintiff", "defendant", "jurisdiction", "statute", "clause",
            "precedent", "ruling", "judgment", "appeal", "injunction",
            "liability", "indemnification", "breach", "contract", "tort",
            "negligence", "damages", "attorney", "counsel", "court",
            "hereby", "whereas", "hereinafter", "notwithstanding",
            "pursuant", "aforementioned", "shall", "covenant", "arbitration",
            "litigation", "settlement", "deposition", "subpoena", "warrant",
            "habeas corpus", "mens rea", "prima facie", "pro bono",
            "amicus", "certiorari", "affidavit", "indictment",
        ],
        "patterns": [
            r"\b\d+\s+U\.S\.\s+\d+\b",              # US citations
            r"\b[A-Z][a-z]+\s+v\.\s+[A-Z][a-z]+\b", # case names
            r"\bSection\s+\d+(?:\.\d+)?\b",          # section refs
            r"\bArt(?:icle)?\.\s+\d+\b",             # articles
            r"\b§\s*\d+\b",                          # section symbol
        ],
        "weight": 1.1,
    },
    Domain.POLICY: {
        "keywords": [
            "policy", "regulation", "governance", "stakeholder", "framework",
            "legislation", "mandate", "compliance", "implementation", "initiative",
            "government", "ministry", "committee", "parliament", "senate",
            "amendment", "directive", "ordinance", "reform", "bilateral",
            "multilateral", "treaty", "convention", "protocol", "agenda",
            "geopolitical", "diplomatic", "sanction", "tariff", "trade",
            "sovereignty", "jurisdiction", "public sector", "ngo", "civil society",
        ],
        "patterns": [
            r"\b[A-Z]{2,8}\s+Act\b",                 # Acts
            r"\bSDG\s*\d+\b",                        # SDGs
            r"\bArticle\s+\d+\b",
            r"\bResolution\s+\d+\b",
        ],
        "weight": 1.0,
    },
    Domain.GENERAL: {
        "keywords": [],
        "patterns": [],
        "weight": 0.1,  # fallback
    },
}


# ─── Classifier ───────────────────────────────────────────────────────────────

class DomainDetector:
    """
    Lightweight domain classifier using keyword frequency + pattern matching.
    No model required — fast, deterministic, explainable.
    """

    def detect(self, text: str) -> Tuple[Domain, float, Dict[str, float]]:
        """
        Returns: (domain, confidence, score_breakdown)
        """
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        word_freq = Counter(words)
        total_words = max(len(words), 1)

        scores: Dict[str, float] = {}

        for domain, config in DOMAIN_SIGNALS.items():
            if domain == Domain.GENERAL:
                continue

            # Keyword score: frequency-normalized
            kw_hits = sum(word_freq.get(kw, 0) for kw in config["keywords"])
            kw_score = (kw_hits / total_words) * 1000 * config["weight"]

            # Pattern score: presence-based
            pattern_hits = 0
            for pattern in config["patterns"]:
                matches = re.findall(pattern, text[:5000])  # scan first 5k chars
                pattern_hits += min(len(matches), 5)  # cap at 5 per pattern
            pattern_score = pattern_hits * 2.0 * config["weight"]

            scores[domain] = round(kw_score + pattern_score, 3)

        if not scores or max(scores.values()) < 0.5:
            return Domain.GENERAL, 0.5, scores

        best_domain = max(scores, key=scores.get)
        best_score = scores[best_domain]
        total_score = sum(scores.values())

        confidence = min(best_score / total_score if total_score > 0 else 0.5, 0.99)
        confidence = round(confidence, 3)

        logger.info(f"Domain detection: {best_domain} (confidence: {confidence:.1%})")
        logger.debug(f"Score breakdown: {scores}")

        return Domain(best_domain), confidence, scores

    def get_domain_label(self, domain: Domain) -> str:
        labels = {
            Domain.CHEMISTRY: "Chemistry & Materials Science",
            Domain.FINANCE: "Finance & Economics",
            Domain.LAW: "Legal & Jurisprudence",
            Domain.POLICY: "Policy & Governance",
            Domain.GENERAL: "General Research",
        }
        return labels.get(domain, "General Research")


detector = DomainDetector()
