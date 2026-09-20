from __future__ import annotations


def shot_requirements(brief: dict) -> list[dict]:
    category=brief.get("category","business")
    if category=="restaurant":
        names=[("hook","hero food/product close-up","1-2 seconds"),("craft","chef/preparation/detail","2-3 seconds"),("experience","real customer/dining atmosphere","2-3 seconds"),("proof","signature dish/service/location","2-3 seconds"),("cta","exterior, booking/order or brand shot","2 seconds")]
    else:
        names=[("hook","strongest product/service visual","1-2 seconds"),("problem","real customer/business context","2-3 seconds"),("solution","product/service in use","2-3 seconds"),("proof","result, people or environment","2-3 seconds"),("cta","brand, website or contact visual","2 seconds")]
    return [{"beat":a,"need":b,"recommended_duration":c,"search_hint":b} for a,b,c in names]
