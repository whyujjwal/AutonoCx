#!/usr/bin/env bash
# ============================================================
# AutonoCX -- Seed the database with demo data
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/packages/backend"

cd "$BACKEND_DIR"

echo "[seed] Seeding database with demo data..."

uv run python -c "
import asyncio
import uuid
from datetime import datetime, UTC

async def seed():
    # ------------------------------------------------------------------
    # Bootstrap: create engine + session
    # ------------------------------------------------------------------
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select, text
    import os

    database_url = os.environ.get(
        'DATABASE_URL',
        'postgresql+asyncpg://autonomocx:autonomocx_dev@localhost:5432/autonomocx',
    )
    engine = create_async_engine(database_url)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    from autonomocx.models.organization import Organization, PlanType
    from autonomocx.models.user import User, UserRole
    from autonomocx.models.agent import AgentConfig
    from autonomocx.models.tool import Tool, RiskLevel
    from autonomocx.models.knowledge import KnowledgeBase
    from autonomocx.core.security import get_password_hash

    async with async_session() as session:
        # Check if demo org already exists
        result = await session.execute(
            select(Organization).where(Organization.slug == 'demo-corp')
        )
        if result.scalar_one_or_none() is not None:
            print('[seed] Demo data already exists -- skipping.')
            await engine.dispose()
            return

        # ── Demo Organization ─────────────────────────────────────
        org = Organization(
            id=uuid.uuid4(),
            name='Demo Corp',
            slug='demo-corp',
            plan=PlanType.GROWTH,
            is_active=True,
            settings={
                'timezone': 'America/New_York',
                'language': 'en',
                'business_hours': {
                    'start': '09:00',
                    'end': '17:00',
                    'days': ['mon', 'tue', 'wed', 'thu', 'fri'],
                },
            },
        )
        session.add(org)
        await session.flush()
        print(f'[seed] Created organization: {org.name} ({org.id})')

        # ── Admin User ────────────────────────────────────────────
        admin = User(
            id=uuid.uuid4(),
            org_id=org.id,
            email='admin@democorp.com',
            password_hash=get_password_hash('admin123!'),
            full_name='Demo Admin',
            role=UserRole.ADMIN,
            is_active=True,
        )
        session.add(admin)
        print(f'[seed] Created admin user: {admin.email} (password: admin123!)')

        # ── Agent Configuration ───────────────────────────────────
        agent = AgentConfig(
            id=uuid.uuid4(),
            org_id=org.id,
            name='Support Agent',
            description='General-purpose customer support agent for Demo Corp',
            system_prompt=(
                'You are a helpful customer support agent for Demo Corp. '
                'Be professional, empathetic, and concise. '
                'If you are unsure about something, say so and offer to escalate. '
                'Never make up information about products or policies.'
            ),
            llm_provider='openai',
            llm_model='gpt-4o',
            temperature=0.3,
            max_tokens=1024,
            is_active=True,
            metadata_={
                'greeting': 'Hello! How can I help you today?',
                'farewell': 'Thank you for contacting Demo Corp. Have a great day!',
            },
        )
        session.add(agent)
        print(f'[seed] Created agent: {agent.name} ({agent.id})')

        # ── Sample Tools ──────────────────────────────────────────
        tools = [
            Tool(
                id=uuid.uuid4(),
                org_id=org.id,
                name='lookup_order',
                display_name='Order Lookup',
                description='Look up an order by order ID or customer email',
                category='order_management',
                parameters_schema={
                    'type': 'object',
                    'properties': {
                        'order_id': {'type': 'string', 'description': 'The order ID'},
                        'email': {'type': 'string', 'description': 'Customer email'},
                    },
                    'required': [],
                },
                endpoint_url='https://api.democorp.com/v1/orders/lookup',
                http_method='GET',
                risk_level=RiskLevel.LOW,
                requires_approval=False,
                is_active=True,
                is_builtin=False,
                version='1.0.0',
            ),
            Tool(
                id=uuid.uuid4(),
                org_id=org.id,
                name='issue_refund',
                display_name='Issue Refund',
                description='Issue a refund for an order. Requires human approval.',
                category='order_management',
                parameters_schema={
                    'type': 'object',
                    'properties': {
                        'order_id': {'type': 'string', 'description': 'The order ID'},
                        'amount': {'type': 'number', 'description': 'Refund amount in USD'},
                        'reason': {'type': 'string', 'description': 'Reason for refund'},
                    },
                    'required': ['order_id', 'amount', 'reason'],
                },
                endpoint_url='https://api.democorp.com/v1/orders/refund',
                http_method='POST',
                risk_level=RiskLevel.HIGH,
                requires_approval=True,
                is_active=True,
                is_builtin=False,
                version='1.0.0',
            ),
            Tool(
                id=uuid.uuid4(),
                org_id=org.id,
                name='search_faq',
                display_name='FAQ Search',
                description='Search the FAQ knowledge base for relevant articles',
                category='knowledge',
                parameters_schema={
                    'type': 'object',
                    'properties': {
                        'query': {'type': 'string', 'description': 'Search query'},
                        'top_k': {'type': 'integer', 'description': 'Number of results', 'default': 5},
                    },
                    'required': ['query'],
                },
                risk_level=RiskLevel.LOW,
                requires_approval=False,
                is_active=True,
                is_builtin=True,
                version='1.0.0',
            ),
        ]
        for tool in tools:
            session.add(tool)
            print(f'[seed] Created tool: {tool.display_name}')

        # ── Sample Knowledge Base ─────────────────────────────────
        kb = KnowledgeBase(
            id=uuid.uuid4(),
            org_id=org.id,
            name='Demo Corp FAQ',
            description='Frequently asked questions and product documentation',
            embedding_model='text-embedding-3-small',
            chunk_size=512,
            chunk_overlap=64,
            is_active=True,
            document_count=0,
            total_chunks=0,
        )
        session.add(kb)
        print(f'[seed] Created knowledge base: {kb.name}')

        await session.commit()

    await engine.dispose()
    print('')
    print('[seed] Seeding complete!')
    print('[seed] Login with: admin@democorp.com / admin123!')

asyncio.run(seed())
"

echo "[seed] Done."
