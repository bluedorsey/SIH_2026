"""Initial four-store schema

Revision ID: 001
Revises: None
Create Date: 2026-09-23

Creates all 4 Postgres schemas (raw, derived, review, reference)
and all tables with columns matching SERVER/DB/models.py exactly.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, TIMESTAMP

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NOW = sa.text("now()")
_UUID = sa.text("gen_random_uuid()")


def upgrade() -> None:
    # ── Create schemas ───────────────────────────────────────────────────
    op.execute("CREATE SCHEMA IF NOT EXISTS raw")
    op.execute("CREATE SCHEMA IF NOT EXISTS derived")
    op.execute("CREATE SCHEMA IF NOT EXISTS review")
    op.execute("CREATE SCHEMA IF NOT EXISTS reference")

    # ═══════════════════════════════════════════════════════════════════════
    #  REFERENCE schema
    # ═══════════════════════════════════════════════════════════════════════
    op.create_table(
        "sites",
        sa.Column("site_code", sa.Text(), primary_key=True),
        sa.Column("site_name", sa.Text(), nullable=False),
        sa.Column("region", sa.Text()),
        sa.Column("site_type", sa.Text()),
        schema="reference",
    )

    op.create_table(
        "life_saving_rules",
        sa.Column("code", sa.Text(), primary_key=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("iogp_number", sa.Integer()),
        sa.Column("oil_internal_aliases", ARRAY(sa.Text())),
        schema="reference",
    )

    op.create_table(
        "precursors",
        sa.Column("code", sa.Text(), primary_key=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("lsr_code", sa.Text(), sa.ForeignKey("reference.life_saving_rules.code")),
        schema="reference",
    )

    op.create_table(
        "thresholds",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("value", sa.Numeric(), nullable=False),
        sa.Column("unit", sa.Text()),
        sa.Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        schema="reference",
    )

    # ═══════════════════════════════════════════════════════════════════════
    #  RAW schema
    # ═══════════════════════════════════════════════════════════════════════
    op.create_table(
        "reports",
        sa.Column("report_id", UUID(as_uuid=True), primary_key=True, server_default=_UUID),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("site_code", sa.Text()),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("raw_text_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("submitted_at", TIMESTAMP(timezone=True)),
        sa.Column("ingested_at", TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        sa.Column("language_hint", sa.Text()),
        sa.Column("pii_scrubbed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metadata", JSONB()),
        schema="raw",
    )
    op.create_index(
        "ix_raw_reports_site_ingested", "reports",
        ["site_code", "ingested_at"], schema="raw",
    )

    # ═══════════════════════════════════════════════════════════════════════
    #  DERIVED schema
    # ═══════════════════════════════════════════════════════════════════════
    op.create_table(
        "verdicts",
        sa.Column("verdict_id", UUID(as_uuid=True), primary_key=True, server_default=_UUID),
        sa.Column("report_id", UUID(as_uuid=True), sa.ForeignKey("raw.reports.report_id"), nullable=False),
        sa.Column("pipeline_version", sa.Text(), nullable=False),
        sa.Column("produced_at", TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        # verdict classification
        sa.Column("verdict", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3)),
        sa.Column("review_required", sa.Boolean(), nullable=False),
        # EEI four-question trace
        sa.Column("q1_high_energy", sa.Boolean()),
        sa.Column("q2_energy_released", sa.Boolean()),
        sa.Column("q3_person_exposed", sa.Boolean()),
        sa.Column("q4_control_effective", sa.Boolean()),
        # safety taxonomy
        sa.Column("lsr_primary", sa.Text()),
        sa.Column("lsr_secondary", ARRAY(sa.Text())),
        sa.Column("activity", sa.Text()),
        sa.Column("hazard", sa.Text()),
        sa.Column("barrier", sa.Text()),
        sa.Column("barrier_status", sa.Text()),
        sa.Column("potential_consequence", sa.Text()),
        sa.Column("explanation", sa.Text()),
        # versioning
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        # rich JSONB columns
        sa.Column("energy_detail", JSONB()),
        sa.Column("uc_ua_detail", JSONB()),
        sa.Column("full_output", JSONB()),
        schema="derived",
    )
    op.create_index(
        "ix_derived_verdicts_report_current", "verdicts",
        ["report_id", "is_current"], schema="derived",
    )
    op.create_index(
        "ix_derived_verdicts_verdict", "verdicts",
        ["verdict"], schema="derived",
        postgresql_where=sa.text("is_current"),
    )
    op.create_index(
        "ix_derived_verdicts_lsr", "verdicts",
        ["lsr_primary"], schema="derived",
        postgresql_where=sa.text("is_current"),
    )

    op.create_table(
        "spans",
        sa.Column("span_id", UUID(as_uuid=True), primary_key=True, server_default=_UUID),
        sa.Column("verdict_id", UUID(as_uuid=True), sa.ForeignKey("derived.verdicts.verdict_id"), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("text_span", sa.Text(), nullable=False),
        sa.Column("char_start", sa.Integer()),
        sa.Column("char_end", sa.Integer()),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("score", sa.Numeric(4, 3)),
        schema="derived",
    )
    op.create_index(
        "ix_derived_spans_verdict", "spans",
        ["verdict_id"], schema="derived",
    )

    op.create_table(
        "precursor_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=_UUID),
        sa.Column("verdict_id", UUID(as_uuid=True), sa.ForeignKey("derived.verdicts.verdict_id"), nullable=False),
        sa.Column("precursor_code", sa.Text(), sa.ForeignKey("reference.precursors.code"), nullable=False),
        sa.Column("similarity", sa.Numeric(4, 3)),
        schema="derived",
    )

    # ═══════════════════════════════════════════════════════════════════════
    #  REVIEW schema
    # ═══════════════════════════════════════════════════════════════════════
    op.create_table(
        "actions",
        sa.Column("action_id", UUID(as_uuid=True), primary_key=True, server_default=_UUID),
        sa.Column("verdict_id", UUID(as_uuid=True), sa.ForeignKey("derived.verdicts.verdict_id"), nullable=False),
        sa.Column("reviewer_id", sa.Text(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("corrected_verdict", sa.Text()),
        sa.Column("corrected_lsr", ARRAY(sa.Text())),
        sa.Column("note", sa.Text()),
        sa.Column("acted_at", TIMESTAMP(timezone=True), nullable=False, server_default=_NOW),
        schema="review",
    )
    op.create_index(
        "ix_review_actions_verdict", "actions",
        ["verdict_id"], schema="review",
    )
    op.create_index(
        "ix_review_actions_reviewer_at", "actions",
        ["reviewer_id", "acted_at"], schema="review",
    )


def downgrade() -> None:
    # Review
    op.drop_index("ix_review_actions_reviewer_at", table_name="actions", schema="review")
    op.drop_index("ix_review_actions_verdict", table_name="actions", schema="review")
    op.drop_table("actions", schema="review")

    # Derived
    op.drop_table("precursor_links", schema="derived")
    op.drop_index("ix_derived_spans_verdict", table_name="spans", schema="derived")
    op.drop_table("spans", schema="derived")
    op.drop_index("ix_derived_verdicts_lsr", table_name="verdicts", schema="derived")
    op.drop_index("ix_derived_verdicts_verdict", table_name="verdicts", schema="derived")
    op.drop_index("ix_derived_verdicts_report_current", table_name="verdicts", schema="derived")
    op.drop_table("verdicts", schema="derived")

    # Raw
    op.drop_index("ix_raw_reports_site_ingested", table_name="reports", schema="raw")
    op.drop_table("reports", schema="raw")

    # Reference
    op.drop_table("thresholds", schema="reference")
    op.drop_table("precursors", schema="reference")
    op.drop_table("life_saving_rules", schema="reference")
    op.drop_table("sites", schema="reference")

    # Drop schemas
    op.execute("DROP SCHEMA IF EXISTS review CASCADE")
    op.execute("DROP SCHEMA IF EXISTS derived CASCADE")
    op.execute("DROP SCHEMA IF EXISTS raw CASCADE")
    op.execute("DROP SCHEMA IF EXISTS reference CASCADE")
