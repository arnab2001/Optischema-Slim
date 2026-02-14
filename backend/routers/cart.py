"""
Cart Router for OptiSchema Slim.
Manages a per-session optimization cart: add/remove items, apply all in a transaction, export as SQL migration.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from connection_manager import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/cart",
    tags=["cart"]
)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class CartItem(BaseModel):
    id: Optional[str] = None
    type: str  # "index" | "rewrite" | "drop"
    sql: str
    description: str
    table: str
    estimated_improvement: Optional[float] = None
    source: Optional[str] = None  # "analysis" | "index-advisor" | "health"


class AddRequest(BaseModel):
    item: CartItem
    tenant_id: Optional[str] = "default"


class RemoveRequest(BaseModel):
    item_id: str
    tenant_id: Optional[str] = "default"


class ClearRequest(BaseModel):
    tenant_id: Optional[str] = "default"


class ApplyRequest(BaseModel):
    tenant_id: Optional[str] = "default"


# ---------------------------------------------------------------------------
# In-memory storage: tenant_id -> list[CartItem dict]
# ---------------------------------------------------------------------------
_carts: Dict[str, List[dict]] = {}


def _get_cart(tenant_id: str) -> List[dict]:
    return _carts.setdefault(tenant_id, [])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("")
async def get_cart(tenant_id: str = "default"):
    """Return current cart contents."""
    items = _get_cart(tenant_id)
    return {"success": True, "items": items, "count": len(items)}


@router.post("/add")
async def add_to_cart(request: AddRequest):
    """Add an item to the cart. Duplicate SQL is rejected."""
    cart = _get_cart(request.tenant_id)
    item_dict = request.item.model_dump()

    # Assign a unique ID if not provided
    if not item_dict.get("id"):
        item_dict["id"] = str(uuid.uuid4())

    # Prevent duplicates (same SQL)
    for existing in cart:
        if existing["sql"].strip().lower() == item_dict["sql"].strip().lower():
            return {"success": False, "message": "Item already in cart", "id": existing["id"]}

    cart.append(item_dict)
    return {"success": True, "id": item_dict["id"], "count": len(cart)}


@router.post("/remove")
async def remove_from_cart(request: RemoveRequest):
    """Remove an item from the cart by ID."""
    cart = _get_cart(request.tenant_id)
    before = len(cart)
    _carts[request.tenant_id] = [i for i in cart if i["id"] != request.item_id]
    removed = before - len(_carts[request.tenant_id])
    return {"success": removed > 0, "removed": removed, "count": len(_carts[request.tenant_id])}


@router.post("/clear")
async def clear_cart(request: ClearRequest):
    """Clear all items from the cart."""
    _carts[request.tenant_id] = []
    return {"success": True, "count": 0}


@router.post("/apply")
async def apply_cart(request: ApplyRequest):
    """
    Apply all cart items in a single database transaction.
    CONCURRENTLY is stripped because it's not allowed inside a transaction block.
    If any statement fails, the entire transaction rolls back.
    """
    cart = _get_cart(request.tenant_id)
    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty")

    pool = await connection_manager.get_pool()
    if not pool:
        raise HTTPException(status_code=400, detail="No active database connection")

    results = []
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                for item in cart:
                    sql = item["sql"]
                    # Strip CONCURRENTLY – not allowed inside a transaction
                    safe_sql = sql.replace("CONCURRENTLY ", "").replace("concurrently ", "")
                    try:
                        await conn.execute(safe_sql)
                        results.append({"id": item["id"], "status": "applied", "sql": safe_sql})
                    except Exception as e:
                        # Transaction will auto-rollback; re-raise to signal failure
                        raise HTTPException(
                            status_code=400,
                            detail=f"Failed on item '{item['description']}': {str(e)}. Transaction rolled back."
                        )

        # Clear the cart after successful apply
        _carts[request.tenant_id] = []
        return {"success": True, "applied": len(results), "results": results}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cart apply failed: {e}")
        raise HTTPException(status_code=500, detail=f"Apply failed: {str(e)}")


@router.get("/export")
async def export_cart(tenant_id: str = "default"):
    """
    Export cart items as a SQL migration script.
    Returns a downloadable .sql file with comments and CONCURRENTLY preserved.
    """
    cart = _get_cart(tenant_id)
    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty")

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    total = len(cart)

    lines = [
        f"-- OptiSchema Slim Migration",
        f"-- Generated: {now}",
        f"-- Items: {total}",
        f"",
        f"BEGIN;",
        f"",
    ]

    for idx, item in enumerate(cart, 1):
        desc = item.get("description", "No description")
        improvement = item.get("estimated_improvement")
        improvement_str = f" (estimated {improvement}% improvement)" if improvement else ""
        lines.append(f"-- [{idx}/{total}] {desc}{improvement_str}")
        lines.append(f"{item['sql']};")
        lines.append("")

    lines.append("COMMIT;")
    lines.append("")

    script = "\n".join(lines)
    return PlainTextResponse(
        content=script,
        media_type="application/sql",
        headers={"Content-Disposition": f"attachment; filename=optischema_migration_{now.replace(' ', '_').replace(':', '')}.sql"}
    )
