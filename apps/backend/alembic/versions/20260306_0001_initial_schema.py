"""initial backend schema

Revision ID: 20260306_0001
Revises:
Create Date: 2026-03-06 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260306_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backend_cms_sites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("site_key", sa.String(), nullable=False),
        sa.Column("draft_json", sa.String(), nullable=False),
        sa.Column("published_json", sa.String(), nullable=False),
        sa.Column("published_version", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_backend_cms_sites_site_key"),
        "backend_cms_sites",
        ["site_key"],
        unique=True,
    )

    op.create_table(
        "backend_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=False),
        sa.Column("printer_id", sa.String(), nullable=False),
        sa.Column("gcode_url", sa.String(), nullable=False),
        sa.Column("parameters_json", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("progress_pct", sa.Float(), nullable=True),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_backend_jobs_job_id"), "backend_jobs", ["job_id"], unique=True)
    op.create_index(op.f("ix_backend_jobs_printer_id"), "backend_jobs", ["printer_id"], unique=False)

    op.create_table(
        "backend_printers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("printer_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_job_id", sa.String(), nullable=True),
        sa.Column("progress_pct", sa.Float(), nullable=True),
        sa.Column("nozzle_temp_c", sa.Float(), nullable=True),
        sa.Column("bed_temp_c", sa.Float(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_backend_printers_printer_id"),
        "backend_printers",
        ["printer_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_backend_printers_printer_id"), table_name="backend_printers")
    op.drop_table("backend_printers")
    op.drop_index(op.f("ix_backend_jobs_printer_id"), table_name="backend_jobs")
    op.drop_index(op.f("ix_backend_jobs_job_id"), table_name="backend_jobs")
    op.drop_table("backend_jobs")
    op.drop_index(op.f("ix_backend_cms_sites_site_key"), table_name="backend_cms_sites")
    op.drop_table("backend_cms_sites")
