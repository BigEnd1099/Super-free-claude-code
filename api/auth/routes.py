from fastapi import APIRouter, Depends

from api.dependencies import require_api_key

from .manager import AccountSession, auth_manager

router = APIRouter()


@router.get("/v1/auth/status")
async def get_auth_status(_auth=Depends(require_api_key)):
    """Return the status of all managed accounts."""
    return {"accounts": auth_manager.get_status()}


@router.post("/v1/auth/session")
async def add_session(session: AccountSession, _auth=Depends(require_api_key)):
    """Manually add a session (e.g. from a cookie capture tool)."""
    auth_manager.add_session(session)
    return {"status": "success", "account_id": session.account_id}
