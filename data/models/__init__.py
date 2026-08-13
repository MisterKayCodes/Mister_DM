from sqlalchemy.orm import declarative_base

Base = declarative_base()

from .account import Account
from .campaign import Campaign
from .template import Template

