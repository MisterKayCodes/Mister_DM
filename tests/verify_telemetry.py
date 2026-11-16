import asyncio
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.database import init_db, AsyncSessionLocal
from services.reporting.telemetry_service import TelemetryService
from data.repositories.reporting.outreach_audit_repo import OutreachAuditRepo

async def main():
    print("1. Initializing database schema...")
    await init_db()
    print("Database initialized successfully.")

    print("\n2. Testing record_dispatch via TelemetryService...")
    session_test = "test_warrior_01"
    res1 = await TelemetryService.record_dispatch(
        session_name=session_test,
        target_username="lead_alpha",
        template_id=101,
        outcome="sent"
    )
    print(f"Recorded first dispatch: id={res1.id}, daily_index={res1.daily_index}, gap={res1.gap_minutes}m")

    res2 = await TelemetryService.record_dispatch(
        session_name=session_test,
        target_username="lead_beta",
        template_id=102,
        outcome="flood_wait",
        error_details="FloodWait 300s"
    )
    print(f"Recorded second dispatch: id={res2.id}, daily_index={res2.daily_index}, outcome={res2.outcome}")

    print("\n3. Testing get_dashboard_summary...")
    dash = await TelemetryService.get_dashboard_summary()
    print("Summary 24h:", dash["summary"])
    print("Alerts:", dash["alerts"])
    print(f"Recent logs count: {len(dash['recent_logs'])}")
    for log in dash["recent_logs"]:
        print(f" - [{log.outcome}] {log.session_name} -> @{log.target_username} (DM #{log.daily_index}, gap {log.gap_minutes}m)")

    print("\n4. Testing get_session_history...")
    history = await TelemetryService.get_session_history(session_test)
    print(f"History count for {session_test}: {len(history)}")
    for h in history:
        print(f" - [{h.outcome}] @{h.target_username} (Template #{h.template_id})")

    assert len(dash["recent_logs"]) >= 2, "Expected at least 2 recent logs"
    assert dash["summary"]["total_sent"] >= 2, "Expected total_sent >= 2"
    assert dash["summary"]["flood_wait_count"] >= 1, "Expected flood_wait_count >= 1"

    print("\n>>> ALL VERIFICATION CHECKS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    asyncio.run(main())
