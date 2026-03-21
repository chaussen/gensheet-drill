"""
routers/questions.py
====================
/api/questions/* endpoints — stub for Iteration 1.
Iteration 4 will add cache inspection / pre-warm endpoints here.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/questions")


@router.get("/templates")
async def list_templates(year_level: int | None = None, strand: str | None = None):
    """Return available template IDs for a given year/strand combination."""
    from docs_loader import get_templates_for, get_all_template_ids
    if year_level and strand:
        templates = get_templates_for(year_level, strand)
        return {"templates": [{"id": t["id"], "topic": t.get("topic"), "vc_code": t.get("vc_code")} for t in templates]}
    return {"template_ids": get_all_template_ids()}
