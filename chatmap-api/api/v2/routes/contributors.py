from fastapi import APIRouter, HTTPException, Response

from api.v2.schemas.contributor import JoinRequest, JoinResponse
from results.error import ContributorRemoved, InvitationNotFound, StoreUnavailable
from store.contributors.store import ContributorStore

router = APIRouter()


@router.post("/invitations/join", status_code=201)
async def join_invitation(
        join: JoinRequest,
        response: Response,
) -> JoinResponse:
    try:
        result = await ContributorStore.join(join.token, join.nickname, join.secret)
    except InvitationNotFound:
        raise HTTPException(status_code=404, detail="Invitation not found.")
    except ContributorRemoved:
        raise HTTPException(status_code=403, detail="Contributor removed.")
    except StoreUnavailable:
        raise HTTPException(status_code=503, detail="Contributor storage unavailable.")

    response.status_code = 201 if result.created else 200

    return JoinResponse(
        contributor_id=result.contributor_id,
        map_id=result.map_id,
        map_name=result.map_name,
    )
