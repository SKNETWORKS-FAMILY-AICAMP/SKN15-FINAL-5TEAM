"""
Alembic Environment Configuration
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import Base and all models
from app.core.db.base import Base
from app.core.config import get_settings

# Import all models to register them with Base
from app.features.sessions.models import Session
from app.features.chat.models import (
    DialogueTurn,
    ConversationSummary,
    UserMemory,
    Entity,
    Relationship,
    EntityMention,
)
from app.features.scenarios.models import (
    Scenarios,
    ScenarioComment,
    ScenarioLike,
    CommentLike,
    ScenarioView,
    ScenarioStage,
    ScenarioMicroBeat,
    ScenarioMission,
    ScenarioRouter,
    ScenarioIntentMapping,
)
from app.features.galleries.models import GalleryImage
from app.features.images.models import ImageMapping
from app.features.images.legacy_models import (
    ImageAsset, ScenarioStageImage, ScenarioDefaultImage,
    ImageMappingRule
)
from app.features.auth.models import User
from app.features.users.models.xp_transaction import XPTransaction
from app.features.game.models import (
    UserEquipment, UserUnlockedImage, RankDefinition,
    GameEvent, MissionRecord
)
from app.features.progression.models import (
    UserInput, UserProgression, UserScenarioProgress,
    StageProgression
)
from app.features.misc.models import (
    SessionSnapshot, ScenarioStatistics, UserFeedback
)
from app.features.users.models import UserCredits
from app.features.logging.models import (
    Log,
    ErrorLog,
    PerformanceMetric,
    TrainingLog,
)

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata
target_metadata = Base.metadata

# Get database URL from settings (using psycopg2 for sync migrations)
settings = get_settings()
# Convert asyncpg URL to psycopg2 URL for Alembic
sync_db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
config.set_main_option("sqlalchemy.url", sync_db_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def include_object(object, name, type_, reflected, compare_to):
    """
    Should you include this object in the autogenerate sweep?

    This function helps Alembic ignore tables that already exist in the database
    but are not perfectly matched with the model definitions.
    """
    # Always include operations from migration files
    if not reflected:
        return True

    # For reflected objects (from database), only show real differences
    # This prevents Alembic from constantly detecting "new" tables that actually exist
    return False


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            # Less strict comparison to avoid false positives
            compare_type=False,
            compare_server_default=False,
            include_object=include_object,
            # Ignore rendering of comments
            render_item=None,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
