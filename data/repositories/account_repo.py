from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from data.models.account import Account

async def add_account(session: AsyncSession, name: str, session_path: str, delay_min: int, delay_max: int) -> tuple[bool, str]:
    """Adds a new account. Returns (success, message)."""
    new_account = Account(
        name=name,
        session_path=session_path,
        delay_min=delay_min,
        delay_max=delay_max
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

async def delete_account(session: AsyncSession, account_id: int) -> bool:
    """Deletes an account by its ID. Returns True if deleted, False if not found."""
    account = await get_account_by_id(session, account_id)
    if account:
        await session.delete(account)
        await session.commit()
        return True
    return False
