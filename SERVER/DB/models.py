"""
SQLAlchemy 2.0 Core table definitions — OILENS four-store schema.

Schemas:  raw  ·  derived  ·  review  ·  reference
All tables use UUID primary keys via gen_random_uuid() on Postgres.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy import (
    MetaData,
    Table,
    Column,
    Text,
    Boolean,
    Integer,
    Numeric,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, TIMESTAMP

#  Schema-specific MetaData objects 
raw_meta = MetaData(schema="raw")
derived_meta = MetaData(schema="derived")
review_meta = MetaData(schema="review")
reference_meta = MetaData(schema="reference")

_uuid_pk = lambda: Column(
    "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
)
_now = sa.text("now()")

#  REFERENCE schema  — editable config / taxonomy

sites = Table(
    "sites",
    reference_meta,
    Column("site_code", Text, primary_key=True),
    Column("site_name", Text, nullable=False),
    Column("region", Text),
    Column("site_type", Text),
)

life_saving_rules = Table(
    "life_saving_rules",
    reference_meta,
    Column("code", Text, primary_key=True),
    Column("display_name", Text, nullable=False),
    Column("iogp_number", Integer),
    Column("oil_internal_aliases", ARRAY(Text)),
)

precursors = Table(
    "precursors",
    reference_meta,
    Column("code", Text, primary_key=True),
    Column("display_name", Text, nullable=False),
    Column(
        "lsr_code",
        Text,
        ForeignKey("reference.life_saving_rules.code"),
    ),
)

thresholds = Table(
    "thresholds",
    reference_meta,
    Column("key", Text, primary_key=True),
    Column("value", Numeric, nullable=False),
    Column("unit", Text),
    Column("updated_at", TIMESTAMP(timezone=True), nullable=False, server_default=_now),
)

#  RAW schema  — immutable, append-only, source of truth

reports = Table(
    "reports",
    raw_meta,
    Column("report_id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    Column("source", Text, nullable=False),
    Column("site_code", Text),
    Column("raw_text", Text, nullable=False),
    Column("raw_text_hash", Text, nullable=False, unique=True),
    Column("submitted_at", TIMESTAMP(timezone=True)),
    Column("ingested_at", TIMESTAMP(timezone=True), nullable=False, server_default=_now),
    Column("language_hint", Text),
    Column("pii_scrubbed", Boolean, nullable=False, server_default=sa.text("false")),
    Column("metadata", JSONB),
    Index("ix_raw_reports_site_ingested", "site_code", "ingested_at"),
)

#  DERIVED schema  — versioned model output

verdicts = Table(
    "verdicts",
    derived_meta,
    Column("verdict_id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    Column("report_id", UUID(as_uuid=True), ForeignKey("raw.reports.report_id"), nullable=False),
    Column("pipeline_version", Text, nullable=False),
    Column("produced_at", TIMESTAMP(timezone=True), nullable=False, server_default=_now),
    # verdict classification
    Column("verdict", Text, nullable=False),
    Column("confidence", Numeric(4, 3)),
    Column("review_required", Boolean, nullable=False),
    # EEI four-question trace
    Column("q1_high_energy", Boolean),
    Column("q2_energy_released", Boolean),
    Column("q3_person_exposed", Boolean),
    Column("q4_control_effective", Boolean),
    # safety taxonomy
    Column("lsr_primary", Text),
    Column("lsr_secondary", ARRAY(Text)),
    Column("activity", Text),
    Column("hazard", Text),
    Column("barrier", Text),
    Column("barrier_status", Text),
    Column("potential_consequence", Text),
    Column("explanation", Text),
    # versioning: exactly one current row per report_id
    Column("is_current", Boolean, nullable=False, server_default=sa.text("true")),
    # energy details (stored as JSONB for flexibility)
    Column("energy_detail", JSONB),
    # UC/UA classification
    Column("uc_ua_detail", JSONB),
    # full pipeline output for debugging
    Column("full_output", JSONB),
    Index("ix_derived_verdicts_report_current", "report_id", "is_current"),
    Index("ix_derived_verdicts_verdict", "verdict", postgresql_where=sa.text("is_current")),
    Index("ix_derived_verdicts_lsr", "lsr_primary", postgresql_where=sa.text("is_current")),
)

spans = Table(
    "spans",
    derived_meta,
    Column("span_id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    Column("verdict_id", UUID(as_uuid=True), ForeignKey("derived.verdicts.verdict_id"), nullable=False),
    Column("role", Text, nullable=False),
    Column("text_span", Text, nullable=False),
    Column("char_start", Integer),
    Column("char_end", Integer),
    Column("source", Text, nullable=False),
    Column("score", Numeric(4, 3)),
    Index("ix_derived_spans_verdict", "verdict_id"),
)

precursor_links = Table(
    "precursor_links",
    derived_meta,
    Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    Column("verdict_id", UUID(as_uuid=True), ForeignKey("derived.verdicts.verdict_id"), nullable=False),
    Column("precursor_code", Text, ForeignKey("reference.precursors.code"), nullable=False),
    Column("similarity", Numeric(4, 3)),
)


#  REVIEW schema  — append-only human actions


actions = Table(
    "actions",
    review_meta,
    Column("action_id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
    Column("verdict_id", UUID(as_uuid=True), ForeignKey("derived.verdicts.verdict_id"), nullable=False),
    Column("reviewer_id", Text, nullable=False),
    Column("action", Text, nullable=False),
    Column("corrected_verdict", Text),
    Column("corrected_lsr", ARRAY(Text)),
    Column("note", Text),
    Column("acted_at", TIMESTAMP(timezone=True), nullable=False, server_default=_now),
    Index("ix_review_actions_verdict", "verdict_id"),
    Index("ix_review_actions_reviewer_at", "reviewer_id", "acted_at"),
)

#  Convenience collections 
ALL_METADATA = [raw_meta, derived_meta, review_meta, reference_meta]
