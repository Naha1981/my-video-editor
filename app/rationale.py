from __future__ import annotations
from typing import Any

def build_edit_rationale(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Create concise, inspectable explanations for the Director's major choices."""
    rows=[]
    ranked={x.get("id"):x for x in plan.get("shots_ranked",[])}
    for index,item in enumerate(plan.get("timeline",[]),1):
        if item.get("type")=="logo":
            rows.append({"step":index,"type":"brand","decision":"Finish with NahaLabs brand close","why":"The creative brief requests a branded close.","evidence":"logo end-card rule","confidence":"high"})
            continue
        clip=ranked.get(item.get("clip_id"),{})
        reasons=clip.get("reasons") or item.get("reasons") or []
        intent=item.get("creative_intent","build")
        fit=float(item.get("intent_fit",0) or 0)
        why=f"Selected for the {intent.replace('_',' ')} beat."
        if fit: why+=f" Visual intent fit is {fit:.0%}."
        if reasons: why+=" Supporting evidence: "+str(reasons[0])+"."
        rows.append({"step":index,"type":"shot","clip_id":item.get("clip_id"),"decision":f"Use {item.get('filename','source clip')} for {intent.replace('_',' ')}","why":why,"evidence":reasons[:3],"confidence":"high" if fit>=.7 else ("medium" if fit>=.4 else "heuristic")})
    return rows
