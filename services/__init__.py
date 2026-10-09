"""
Services Package — Master Barrel Exporter
Re-exports all domain services for backward-compatibility and clean imports.
"""

from .campaigns import CampaignService, SchedulerService, TemplateService
from .leads import (
    TargetService,
    IntakeService,
    TriageService,
    IntelligenceService,
    PainTagService,
    RelationshipService,
    ArcService,
)
from .messaging import MessageService
from .accounts import AccountService, BlacklistService
from .notifications import AlertService
from .reporting import StatsService

__all__ = [
    # Campaigns
    "CampaignService",
    "SchedulerService",
    "TemplateService",
    # Leads
    "TargetService",
    "IntakeService",
    "TriageService",
    "IntelligenceService",
    "PainTagService",
    "RelationshipService",
    "ArcService",
    # Messaging
    "MessageService",
    # Accounts
    "AccountService",
    "BlacklistService",
    # Notifications
    "AlertService",
    # Reporting
    "StatsService",
]
