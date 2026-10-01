"""Initialize paper intelligence tables.

Revision ID: 20261001
Revises:
Create Date: 2026-10-01 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20261001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "papers",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("sha256", sa.String(length=128), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_papers_id"), "papers", ["id"], unique=False)
    op.create_index(op.f("ix_papers_sha256"), "papers", ["sha256"], unique=False)

    op.create_table(
        "experiments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id"), nullable=False),
        sa.Column("experiment_key", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("extraction_confidence", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_experiments_id"), "experiments", ["id"], unique=False)

    op.create_table(
        "experiment_parameters",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "experiment_id",
            sa.Integer(),
            sa.ForeignKey("experiments.id"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(length=128), nullable=False),
        sa.Column("field_value", sa.JSON(), nullable=True),
        sa.Column("value_type", sa.String(length=32), nullable=True),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_experiment_parameters_id"),
        "experiment_parameters",
        ["id"],
        unique=False,
    )

    op.create_table(
        "evidence",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "experiment_id",
            sa.Integer(),
            sa.ForeignKey("experiments.id"),
            nullable=False,
        ),
        sa.Column("field", sa.String(length=128), nullable=False),
        sa.Column("value", sa.JSON(), nullable=True),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=True),
        sa.Column("source_label", sa.String(length=128), nullable=True),
        sa.Column("quote", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_evidence_id"), "evidence", ["id"], unique=False)


def downgrade() -> None:
    op.drop_table("evidence")
    op.drop_table("experiment_parameters")
    op.drop_table("experiments")
    op.drop_table("papers")
