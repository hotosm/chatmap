from fastapi import APIRouter, Response
from hotosm_auth_fastapi import CurrentUser

from api.v2.errors import call_store
from api.v2.schemas.rules import MAX_RULES, RuleFields, RuleItem, RulesResponse
from store.message_rules_store import MessageRulesStore
from store.message_suggestions_store import MessageSuggestionsStore

router = APIRouter()


def _rule_item(row) -> RuleItem:
    return RuleItem(
        id=row.id,
        description=row.description,
        enabled=row.enabled,
        conditions=row.conditions,
        actions=row.actions,
    )


@router.get("/maps/{map_id}/rules")
async def read_rules(map_id: str, user: CurrentUser) -> RulesResponse:
    rows = await call_store(MessageRulesStore.rules(map_id, user.id))
    return RulesResponse(rules=[_rule_item(row) for row in rows])


@router.post("/maps/{map_id}/rules", status_code=201)
async def create_rule(map_id: str, rule: RuleFields, user: CurrentUser) -> RuleItem:
    row = await call_store(MessageRulesStore.create_rule(map_id, user.id, rule.model_dump(), MAX_RULES))
    await MessageSuggestionsStore.reread(map_id)
    return _rule_item(row)


@router.put("/maps/{map_id}/rules/{rule_id}")
async def update_rule(map_id: str, rule_id: str, rule: RuleFields, user: CurrentUser) -> RuleItem:
    row = await call_store(MessageRulesStore.update_rule(map_id, rule_id, user.id, rule.model_dump()))
    await MessageSuggestionsStore.reread(map_id)
    return _rule_item(row)


@router.delete("/maps/{map_id}/rules/{rule_id}", status_code=204)
async def remove_rule(map_id: str, rule_id: str, user: CurrentUser) -> Response:
    await call_store(MessageRulesStore.remove_rule(map_id, rule_id, user.id))
    await MessageSuggestionsStore.reread(map_id)
    return Response(status_code=204)
