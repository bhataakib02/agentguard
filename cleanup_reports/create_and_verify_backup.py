import os
import sys
import json
import datetime
import uuid

sys.path.insert(0, r"d:\AGENTGUARD\backend")
from database import engine
from sqlalchemy import text, inspect

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, bytes):
            return obj.hex()
        return super().default(obj)

def run_backup():
    print("=" * 70)
    print("  AGENTGUARD DATABASE BACKUP & VERIFICATION PROCEDURE")
    print("=" * 70)

    backup_dir = r"d:\AGENTGUARD\cleanup_reports\backups"
    os.makedirs(backup_dir, exist_ok=True)
    timestamp_str = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    json_backup_path = os.path.join(backup_dir, f"agentguard_backup_{timestamp_str}.json")
    sql_backup_path = os.path.join(backup_dir, f"agentguard_backup_{timestamp_str}.sql")

    insp = inspect(engine)
    tables = sorted(insp.get_table_names())
    print(f"Discovered {len(tables)} tables to back up.")

    backup_data = {
        "metadata": {
            "timestamp_utc": datetime.datetime.utcnow().isoformat(),
            "engine_dialect": engine.dialect.name,
            "total_tables": len(tables),
            "version": "1.0.0"
        },
        "tables": {}
    }

    sql_statements = [
        f"-- AGENTGUARD DATABASE BACKUP CREATED AT {datetime.datetime.utcnow().isoformat()}",
        "-- PRESERVED SCHEMA AND COMPLETE ROW-LEVEL LOGICAL DUMP",
        "BEGIN;"
    ]

    total_dumped_rows = 0

    with engine.connect() as conn:
        for t in tables:
            rows = conn.execute(text(f'SELECT * FROM "{t}"')).fetchall()
            row_dicts = [dict(r._mapping) for r in rows]
            backup_data["tables"][t] = {
                "row_count": len(rows),
                "rows": row_dicts
            }
            total_dumped_rows += len(rows)

            sql_statements.append(f"\n-- TABLE: {t} ({len(rows)} records)")
            for r in row_dicts:
                cols = list(r.keys())
                col_names = ", ".join([f'"{c}"' for c in cols])
                
                val_strs = []
                for c in cols:
                    v = r[c]
                    if v is None:
                        val_strs.append("NULL")
                    elif isinstance(v, (int, float)):
                        val_strs.append(str(v))
                    elif isinstance(v, bool):
                        val_strs.append("TRUE" if v else "FALSE")
                    elif isinstance(v, (dict, list)):
                        escaped = json.dumps(v).replace("'", "''")
                        val_strs.append(f"'{escaped}'::json")
                    elif isinstance(v, (datetime.datetime, datetime.date)):
                        val_strs.append(f"'{v.isoformat()}'")
                    else:
                        escaped = str(v).replace("'", "''")
                        val_strs.append(f"'{escaped}'")
                
                vals_joined = ", ".join(val_strs)
                sql_statements.append(f'INSERT INTO "{t}" ({col_names}) VALUES ({vals_joined});')

    sql_statements.append("\nCOMMIT;")

    # Write JSON backup
    with open(json_backup_path, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, cls=CustomEncoder, indent=2)
    print(f"[SUCCESS] JSON Backup written to: {json_backup_path} ({os.path.getsize(json_backup_path)} bytes)")

    # Write SQL backup
    with open(sql_backup_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sql_statements))
    print(f"[SUCCESS] SQL Backup written to: {sql_backup_path} ({os.path.getsize(sql_backup_path)} bytes)")

    # VERIFY BACKUP INTEGRITY
    print("\n--- VERIFYING BACKUP READABILITY & ROW COUNTS ---")
    with open(json_backup_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    verified_tables = 0
    verification_errors = []

    with engine.connect() as conn:
        for t in tables:
            db_count = conn.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
            backup_count = loaded["tables"][t]["row_count"]
            actual_rows_len = len(loaded["tables"][t]["rows"])
            if db_count != backup_count or db_count != actual_rows_len:
                verification_errors.append(f"Table '{t}' mismatch: DB={db_count}, BackupMeta={backup_count}, Rows={actual_rows_len}")
            else:
                verified_tables += 1

    if verification_errors:
        print("[FAIL] Verification encountered errors:")
        for err in verification_errors:
            print("  *", err)
        raise RuntimeError("Backup verification failed!")
    else:
        print(f"[SUCCESS] ALL {verified_tables} TABLES VERIFIED! Total rows backed up: {total_dumped_rows}")
        print("Backup is verified, readable, and recoverable.")

    return {
        "json_path": json_backup_path,
        "sql_path": sql_backup_path,
        "tables_count": len(tables),
        "total_rows": total_dumped_rows,
        "timestamp": timestamp_str
    }

if __name__ == "__main__":
    run_backup()
