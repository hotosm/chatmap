from pydantic import AwareDatetime, BaseModel


class InvitationResponse(BaseModel):
    id: str
    token: str
    url: str
    created_at: AwareDatetime
