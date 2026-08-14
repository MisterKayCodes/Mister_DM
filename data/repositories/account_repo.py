import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from data.models.account import Account
from data.models.campaign import Campaign

async def add_account(session: AsyncSession, name: str, session_string: str, delay_min: int, delay_max: int, daily_limit: int = 40) -> tuple[bool, str]:
    """Adds a new account. Returns (success, message)."""
    new_account = Account(
        name=name,
        session_string=session_string,
        delay_min=delay_min,
        delay_max=delay_max,
        daily_limit=daily_limit,
        messages_sent_today=0,
        last_reset_date=datetime.date.today()
    )
    session.add(new_account)
    try:
        await session.commit()
        return True, "Account created successfully."
    except IntegrityError:
        await session.rollback()
        return False, f"Account with name '{name}' already exists."
    except Exception as e:
        await session.rollback()
        return False, f"Error creating account: {e}"

async def get_all_accounts(session: AsyncSession) -> list[Account]:
    """Retrieves all accounts."""
    result = await session.execute(select(Account))
    return list(result.scalars().all())

async def get_account_by_id(session: AsyncSession, account_id: int) -> Account | None:
    """Retrieves an account by its ID."""
    result = await session.execute(select(Account).where(Account.id == account_id))
    return result.scalar_one_or_none()

async def get_account_by_name(session: AsyncSession, name: str) -> Account | None:
    """Retrieves an account by its exact name."""
    result = await session.execute(select(Account).where(Account.name == name))
    return result.scalar_one_or_none()

async def delete_account(session: AsyncSession, account_id: int) -> tuple[bool, str]:
    """Deletes an account by its ID. Returns (success, message)."""
    # Check for campaigns
    campaigns = await session.execute(select(Campaign).where(Campaign.account_id == account_id))
    if campaigns.scalars().first():
        return False, "This account is used by campaigns. Delete or reassign them first."

    account = await get_account_by_id(session, account_id)
    if account:
        await session.delete(account)
        await session.commit()
        return True, "Deleted."
    return False, "Account not found."

async def increment_daily_counter(session: AsyncSession, account_id: int) -> None:
    """Increments the messages_sent_today counter by 1."""
    account = await get_account_by_id(session, account_id)
    if account:
        account.messages_sent_today = (account.messages_sent_today or 0) + 1

async def reset_daily_counter(session: AsyncSession, account_id: int) -> None:
    """Resets the counter and updates last_reset_date to today."""
    account = await get_account_by_id(session, account_id)
    if account:
        account.messages_sent_today = 0
        account.last_reset_date = datetime.date.today()

async def reset_daily_counter_if_needed(session: AsyncSession, account_id: int) -> bool:
    """Resets counter if last_reset_date is before today. Returns True if reset happened."""
    account = await get_account_by_id(session, account_id)
    if not account:
        return False
    today = datetime.date.today()
    if account.last_reset_date is None or account.last_reset_date < today:
        account.messages_sent_today = 0
        account.last_reset_date = today
        return True
    return False

async def get_remaining_quota(session: AsyncSession, account_id: int) -> int:
    """Returns how many DMs this account can still send today."""
    account = await get_account_by_id(session, account_id)
    if not account:
        return 0
    limit = account.daily_limit or 40
    sent = account.messages_sent_today or 0
    return max(0, limit - sent)
