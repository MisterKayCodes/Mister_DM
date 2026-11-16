# Repository barrel — re-exports all domain repo modules so callers using
# `from data.repositories import <repo_name>` continue to work unchanged.
from data.repositories.accounts import account_repo, blacklist_repo, personas_repo
from data.repositories.campaigns import campaign_repo, template_repo
from data.repositories.leads import (
    target_repo, pain_tag_repo, intel_repo, intents_repo,
    story_arc_repo, draft_repo, relationship_chats_repo,
    relationship_messages_repo, mirror_observations_repo
)
from data.repositories.messaging import message_repo
from data.repositories.reporting import stats_repo, OutreachAuditRepo
from data.repositories.settings import settings_repo
