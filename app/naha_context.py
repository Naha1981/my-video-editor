from __future__ import annotations

import re
from typing import Any


LANES = {
    "intelligent_solutions": {
        "label": "Intelligent Solutions",
        "offers": [
            "lead_machine",
            "ai_employee",
            "ai_automation",
            "revenue_intelligence",
            "sales_intelligence",
            "whatsapp_business_system",
            "custom_intelligent_solution",
        ],
    },
    "enterprise_intelligence": {
        "label": "Enterprise Intelligence",
        "offers": [
            "cargoiq",
            "financial_intelligence",
            "retail_brand_intelligence",
            "operations_intelligence",
            "supply_chain_intelligence",
            "geospatial_intelligence",
            "enterprise_ai_agents",
            "custom_enterprise_system",
        ],
    },
}

PRODUCTS = {
    "cargoiq": {"lane": "enterprise_intelligence", "label": "CargoIQ"},
    "flavourly": {"lane": "intelligent_solutions", "label": "Flavourly"},
    "orderly": {"lane": "intelligent_solutions", "label": "Orderly"},
    "lead_machine": {"lane": "intelligent_solutions", "label": "Lead Machine"},
    "ai_employee": {"lane": "intelligent_solutions", "label": "AI Employee"},
    "revenue_intelligence": {"lane": "intelligent_solutions", "label": "Revenue Intelligence"},
    "custom": {"lane": "enterprise_intelligence", "label": "Custom Intelligent System"},
}

OBJECTIVES = {
    "lead_gen": "Generate qualified opportunities",
    "lead_generation": "Generate qualified opportunities",
    "revenue_recovery": "Recover missed or leaking revenue",
    "awareness": "Build awareness and recognition",
    "bookings": "Drive bookings or enquiries",
    "sales": "Move qualified opportunities toward a sale",
    "proof": "Demonstrate evidence, capability or results",
    "recruitment": "Attract suitable candidates",
    "education": "Explain a complex idea clearly",
    "engagement": "Increase meaningful customer engagement",
    "retention": "Increase customer retention",
}

FORMATS = {
    "facebook_ad": "Facebook ad",
    "instagram_reel": "Instagram Reel",
    "reel": "Short-form Reel",
    "tiktok": "TikTok",
    "youtube_short": "YouTube Short",
    "linkedin": "LinkedIn",
    "website_hero": "Website hero video",
    "case_study": "Case study",
    "demo": "Product demo",
    "ugc_video": "UGC-style video",
    "cinematic": "Cinematic video",
}

AUTHENTICITY_PROFILE = {
    "id": "nahalabs-authentic",
    "name": "NahaLabs Authenticity",
    "requirements": [
        "South African context where relevant",
        "natural human appearance and movement",
        "realistic local architecture and environments",
        "natural lighting, weather and material imperfections",
        "credible local accents and dialogue when present",
        "avoid synthetic or over-polished AI aesthetics",
        "preserve believable imperfections rather than smoothing everything",
    ],
}

AUTHENTICITY_ALIASES = {
    "nahalabs-authentic",
    "south-african-authenticity",
    "sa-authentic",
    "authentic",
}

GROWTH_LOOP = [
    "content",
    "distribution",
    "leads",
    "sales",
    "revenue",
    "analytics",
]

OPERATING_LOOP = ["find", "understand", "act", "learn"]


def _tokens(prompt: str) -> list[str]:
    return [
        re.sub(r"[^a-z0-9]+", "_", x).strip("_")
        for x in re.split(r"[\s,/]+", (prompt or "").strip().lower())
        if x
    ]


def _slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return value


def parse_commands(command: str = "", prompt: str = "") -> dict[str, Any]:
    raw = " ".join(x for x in [command, prompt] if x).strip()
    tokens = _tokens(raw)

    product = None
    for key in PRODUCTS:
        if key in tokens or f"/{key}" in raw.lower() or f'/{key.replace("_", "-")}' in raw.lower():
            product = key
            break

    objective = None
    for key in OBJECTIVES:
        if key in tokens or f"/{key}" in raw.lower() or f'/{key.replace("_", "-")}' in raw.lower():
            objective = key
            break

    format_name = None
    for key in FORMATS:
        if key in tokens or f"/{key}" in raw.lower() or f'/{key.replace("_", "-")}' in raw.lower():
            format_name = key
            break

    authenticity = any(
        alias in raw.lower() or f"/{alias}" in raw.lower()
        for alias in AUTHENTICITY_ALIASES
    )

    lane = PRODUCTS.get(product, {}).get("lane") if product else None
    if not lane:
        lane = "enterprise_intelligence" if any(
            x in raw.lower()
            for x in ["enterprise", "cargoiq", "financial intelligence", "supply chain", "operations intelligence"]
        ) else "intelligent_solutions"

    return {
        "product": product,
        "product_label": PRODUCTS.get(product, {}).get("label") if product else None,
        "lane": lane,
        "lane_label": LANES[lane]["label"],
        "objective": objective,
        "objective_label": OBJECTIVES.get(objective) if objective else None,
        "format": format_name,
        "format_label": FORMATS.get(format_name) if format_name else None,
        "authenticity_profile": AUTHENTICITY_PROFILE["id"] if authenticity else None,
        "authenticity": AUTHENTICITY_PROFILE if authenticity else None,
        "growth_loop": list(GROWTH_LOOP),
        "operating_loop": list(OPERATING_LOOP),
        "raw_command": command.strip(),
    }


def compile_context(
    command: str = "",
    prompt: str = "",
    brief: dict[str, Any] | None = None,
) -> dict[str, Any]:
    context = parse_commands(command, prompt)
    brief = brief or {}

    if not context["product"] and brief.get("product"):
        product = _slug(str(brief["product"]))
        if product in PRODUCTS:
            context["product"] = product
            context["product_label"] = PRODUCTS[product]["label"]
            context["lane"] = PRODUCTS[product]["lane"]
            context["lane_label"] = LANES[context["lane"]]["label"]

    if not context["objective"] and brief.get("objective"):
        key = _slug(str(brief["objective"]))
        if key in OBJECTIVES:
            context["objective"] = key
            context["objective_label"] = OBJECTIVES[key]

    if not context["format"] and brief.get("format"):
        key = _slug(str(brief["format"]))
        if key in FORMATS:
            context["format"] = key
            context["format_label"] = FORMATS[key]

    if not context["authenticity_profile"] and brief.get("authenticity"):
        context["authenticity_profile"] = AUTHENTICITY_PROFILE["id"]
        context["authenticity"] = AUTHENTICITY_PROFILE

    return context
