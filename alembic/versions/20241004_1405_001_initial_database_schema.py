"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2024-10-04 14:05:00.000000

Creates all tables as specified in MD file:
- repositories
- issues 
- claims
- activity_log
- progress_tracking
- queue_jobs

With all indexes, constraints, and relationships
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables with proper constraints and indexes"""
    
    # repositories table
    op.create_table('repositories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('github_repo_id', sa.Integer(), nullable=False),
        sa.Column('owner', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('is_monitored', sa.Boolean(), nullable=True, default=True),
        sa.Column('grace_period_days', sa.Integer(), nullable=True, default=7),
        sa.Column('nudge_count', sa.Integer(), nullable=True, default=2),
        sa.Column('notification_settings', sa.JSON(), nullable=True),
        sa.Column('claim_detection_threshold', sa.Integer(), nullable=True, default=75),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('github_repo_id'),
        sa.CheckConstraint('grace_period_days > 0', name='ck_repositories_grace_period_positive'),
        sa.CheckConstraint('nudge_count >= 0', name='ck_repositories_nudge_count_non_negative'),
        sa.CheckConstraint('claim_detection_threshold BETWEEN 0 AND 100', name='ck_repositories_threshold_range')
    )
    op.create_index('ix_repositories_is_monitored', 'repositories', ['is_monitored'])
    op.create_index('ix_repositories_owner_name', 'repositories', ['owner', 'name'])
    
    # issues table
    op.create_table('issues',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('github_repo_id', sa.Integer(), nullable=False),
        sa.Column('github_issue_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, default='open'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('github_data', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['github_repo_id'], ['repositories.github_repo_id'], 
                              ondelete='CASCADE', name='fk_issues_repository'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('github_repo_id', 'github_issue_number', name='uq_issues_repo_number')
    )
    op.create_index('ix_issues_status', 'issues', ['status'])
    op.create_index('ix_issues_repo_id', 'issues', ['github_repo_id'])
    op.create_index('ix_issues_updated_at', 'issues', ['updated_at'])
    
    # claims table
    op.create_table('claims',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('issue_id', sa.Integer(), nullable=False),
        sa.Column('github_user_id', sa.Integer(), nullable=False),
        sa.Column('github_username', sa.String(), nullable=False),
        sa.Column('claim_comment_id', sa.Integer(), nullable=True),
        sa.Column('claim_text', sa.Text(), nullable=True),
        sa.Column('claim_timestamp', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, default='active'),
        sa.Column('first_nudge_sent_at', sa.DateTime(), nullable=True),
        sa.Column('last_activity_timestamp', sa.DateTime(), nullable=True),
        sa.Column('auto_release_timestamp', sa.DateTime(), nullable=True),
        sa.Column('release_reason', sa.String(), nullable=True),
        sa.Column('confidence_score', sa.Integer(), nullable=True),
        sa.Column('context_metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['issue_id'], ['issues.id'], ondelete='CASCADE', name='fk_claims_issue'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('confidence_score BETWEEN 0 AND 100', name='ck_claims_confidence_range'),
        sa.CheckConstraint("status IN ('active', 'inactive', 'completed', 'released')", name='ck_claims_status_valid')
    )
    op.create_index('ix_claims_status', 'claims', ['status'])
    op.create_index('ix_claims_issue_user', 'claims', ['issue_id', 'github_user_id'])
    op.create_index('ix_claims_last_activity', 'claims', ['last_activity_timestamp'])
    op.create_index('ix_claims_username', 'claims', ['github_username'])
    
    # activity_log table
    op.create_table('activity_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('claim_id', sa.Integer(), nullable=False),
        sa.Column('activity_type', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id'], ondelete='CASCADE', name='fk_activity_log_claim'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("activity_type IN ('progress_nudge', 'auto_release', 'comment', 'claim_detected', 'progress_update', 'timer_reset', 'manual_nudge_triggered', 'manual_release', 'progress_detected')", 
                          name='ck_activity_log_type_valid')
    )
    op.create_index('ix_activity_log_claim_id', 'activity_log', ['claim_id'])
    op.create_index('ix_activity_log_timestamp', 'activity_log', ['timestamp'])
    op.create_index('ix_activity_log_type', 'activity_log', ['activity_type'])
    
    # progress_tracking table
    op.create_table('progress_tracking',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('claim_id', sa.Integer(), nullable=False),
        sa.Column('pr_number', sa.Integer(), nullable=True),
        sa.Column('pr_status', sa.String(), nullable=True),
        sa.Column('commit_count', sa.Integer(), nullable=True, default=0),
        sa.Column('last_commit_date', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('detected_from', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.id'], ondelete='CASCADE', name='fk_progress_tracking_claim'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('claim_id', name='uq_progress_tracking_claim'),
        sa.CheckConstraint('commit_count >= 0', name='ck_progress_tracking_commit_count_non_negative'),
        sa.CheckConstraint("pr_status IS NULL OR pr_status IN ('open', 'closed', 'merged')", name='ck_progress_tracking_pr_status_valid'),
        sa.CheckConstraint("detected_from IS NULL OR detected_from IN ('ecosyste_ms_api', 'github_api')", name='ck_progress_tracking_detected_from_valid')
    )
    op.create_index('ix_progress_tracking_updated_at', 'progress_tracking', ['updated_at'])
    
    # queue_jobs table
    op.create_table('queue_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_type', sa.String(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=True, default='pending'),
        sa.Column('retry_count', sa.Integer(), nullable=True, default=0),
        sa.Column('max_retries', sa.Integer(), nullable=True, default=3),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("job_type IN ('nudge_check', 'progress_check', 'auto_release_check', 'comment_analysis', 'dead_letter')", 
                          name='ck_queue_jobs_type_valid'),
        sa.CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed', 'dead_letter')", 
                          name='ck_queue_jobs_status_valid'),
        sa.CheckConstraint('retry_count >= 0', name='ck_queue_jobs_retry_count_non_negative'),
        sa.CheckConstraint('max_retries >= 0', name='ck_queue_jobs_max_retries_non_negative')
    )
    op.create_index('ix_queue_jobs_scheduled_at', 'queue_jobs', ['scheduled_at'])
    op.create_index('ix_queue_jobs_status', 'queue_jobs', ['status'])
    op.create_index('ix_queue_jobs_job_type', 'queue_jobs', ['job_type'])
    op.create_index('ix_queue_jobs_status_scheduled', 'queue_jobs', ['status', 'scheduled_at'])


def downgrade() -> None:
    """Drop all tables in reverse dependency order"""
    op.drop_table('queue_jobs')
    op.drop_table('progress_tracking')
    op.drop_table('activity_log')
    op.drop_table('claims')
    op.drop_table('issues')
    op.drop_table('repositories')