from fastapi import APIRouter, HTTPException
from hotosm_auth_fastapi import CurrentUser

from api.v2.schemas.invitation import InvitationResponse
from results.error import MapNotFound, StoreUnavailable
from store.invitations.store import InvitationStore

INVITATION_URL_SCHEME = "hot-chatmap"

router = APIRouter()


def _invitation_url(token: str) -> str:
    return f"{INVITATION_URL_SCHEME}://join?token={token}"


@router.post("/maps/{map_id}/invitations", status_code=201)
async def generate_invitation(
        map_id: str,
        user: CurrentUser,
) -> InvitationResponse:
    try:
        invitation, token = await InvitationStore.generate(map_id, user.id)
    except MapNotFound:
        raise HTTPException(status_code=404, detail="Map not found.")
    except StoreUnavailable:
        raise HTTPException(status_code=503, detail="Invitation storage unavailable.")

    return InvitationResponse(
        id=invitation.id,
        token=token,
        url=_invitation_url(token),
        created_at=invitation.created_at,
    )
