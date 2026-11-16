from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Domain subpackage imports — models are registered here once via domain paths.
from .accounts.account import Account
from .accounts.blacklist import Blacklist
from .accounts.persona import Persona
from .campaigns.campaign import Campaign
from .campaigns.template import Template
from .leads.target import Target
from .leads.pain_tag import PainTag, target_pain_tags
from .leads.intel_entry import IntelEntry
from .leads.ai_intent import AIIntent
from .leads.story_arc import StoryArc
from .leads.arc_media import ArcMedia
from .leads.draft_reply import DraftReply
from .leads.relationship_chat import RelationshipChat
from .leads.relationship_message import RelationshipMessage
from .leads.mirror_observation_buffer import MirrorObservationBuffer
from .messaging.message import MessageLog
from .settings.system_setting import SystemSetting
