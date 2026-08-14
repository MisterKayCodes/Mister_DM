from sqlalchemy.orm import declarative_base

Base = declarative_base()

from .account import Account
from .campaign import Campaign
from .template import Template
from .target import Target
from .pain_tag import PainTag

