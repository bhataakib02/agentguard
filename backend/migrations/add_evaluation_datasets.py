"""
AGENTGUARD Migration: Add Evaluation Datasets and Evaluation Dataset Records Tables.
Safe, idempotent migration for PostgreSQL and SQLite.
Enforces tenant isolation, relational linkage, and duplicate protection.
"""

import sys
import os
from sqlalchemy import text, inspect

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import engine, SessionLocal, Base
import models


def run_migration(db_engine=engine):
    print("=== STARTING EVALUATION DATASETS MIGRATION ===")
    inspector = inspect(db_engine)
    existing_tables = inspector.get_table_names()

    # Base.metadata.create_all idempotently creates tables that do not exist
    models.Base.metadata.create_all(
        bind=db_engine,
        tables=[
            models.EvaluationDataset.__table__,
            models.EvaluationDatasetRecord.__table__
        ]
    )

    print("Ensured tables 'evaluation_datasets' and 'evaluation_dataset_records' exist.")
    print("=== MIGRATION COMPLETE ===")


if __name__ == "__main__":
    run_migration()
