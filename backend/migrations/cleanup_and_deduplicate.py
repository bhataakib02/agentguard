import sys
import os
import re
from sqlalchemy import text, inspect

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import SessionLocal, engine
import models

def slugify(text_val: str) -> str:
    if not text_val:
        return "unnamed-org"
    clean = re.sub(r'[^a-zA-Z0-9]+', '-', text_val.strip()).lower().strip('-')
    return clean or "unnamed-org"

def cleanup_and_deduplicate():
    db = SessionLocal()
    print("=== STARTING DATABASE CLEANUP & DEDUPLICATION ===")

    # 1. Ensure 'slug' column exists in database table
    try:
        inspector = inspect(engine)
        columns = [c['name'] for c in inspector.get_columns('organizations')]
        if 'slug' not in columns:
            print("Adding 'slug' column to 'organizations' table...")
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE organizations ADD COLUMN slug VARCHAR"))
                conn.commit()
            print("'slug' column added successfully.")
    except Exception as e:
        print(f"Column check/addition info: {e}")

    # 2. Query all organizations
    all_orgs = db.query(models.Organization).order_by(models.Organization.created_at.asc()).all()
    print(f"Total organizations currently in DB: {len(all_orgs)}")

    # Group orgs by normalized name
    grouped = {}
    for o in all_orgs:
        norm_name = o.name.strip().lower()
        grouped.setdefault(norm_name, []).append(o)

    merged_count = 0
    deleted_count = 0

    for norm_name, org_list in grouped.items():
        if len(org_list) <= 1:
            continue

        # Sort org_list so the best canonical candidate is first
        def score_org(org):
            u_cnt = db.query(models.User).filter(models.User.org_id == org.id).count()
            a_cnt = db.query(models.Agent).filter(models.Agent.org_id == org.id).count()
            admin_score = 10 if org.admin_email else 0
            return (u_cnt * 100) + (a_cnt * 10) + admin_score

        org_list.sort(key=score_org, reverse=True)
        canonical = org_list[0]
        duplicates = org_list[1:]

        print(f"\nConsolidating '{canonical.name}': Canonical ID={canonical.id} (score={score_org(canonical)}), Merging {len(duplicates)} duplicate(s)...")

        for dup in duplicates:
            print(f"  -> Migrating references from Duplicate ID={dup.id} to Canonical ID={canonical.id}")
            
            # Re-link users
            db.query(models.User).filter(models.User.org_id == dup.id).update({"org_id": canonical.id})
            
            # Re-link agents
            db.query(models.Agent).filter(models.Agent.org_id == dup.id).update({"org_id": canonical.id})
            
            # Re-link policies
            db.query(models.Policy).filter(models.Policy.org_id == dup.id).update({"org_id": canonical.id})
            
            # Re-link security incidents
            db.query(models.SecurityIncident).filter(models.SecurityIncident.org_id == dup.id).update({"org_id": canonical.id})
            
            # Re-link API keys
            db.query(models.ApiKey).filter(models.ApiKey.org_id == dup.id).update({"org_id": canonical.id})

            # Re-link report histories & scheduled reports
            db.query(models.ReportHistory).filter(models.ReportHistory.org_id == dup.id).update({"org_id": canonical.id})
            db.query(models.ScheduledReport).filter(models.ScheduledReport.org_id == dup.id).update({"org_id": canonical.id})

            # Re-link or remove duplicate licenses
            dup_lic = db.query(models.License).filter(models.License.org_id == dup.id).all()
            for l in dup_lic:
                db.delete(l)

            dup_lic_usage = db.query(models.LicenseUsage).filter(models.LicenseUsage.org_id == dup.id).all()
            for lu in dup_lic_usage:
                db.delete(lu)

            # Delete the duplicate organization row
            db.delete(dup)
            merged_count += 1
            deleted_count += 1

    db.commit()
    print(f"\nMerged & deleted {deleted_count} duplicate organization rows.")

    # 3. Assign unique slugs to all remaining organizations
    remaining_orgs = db.query(models.Organization).order_by(models.Organization.created_at.asc()).all()
    used_slugs = set()

    for o in remaining_orgs:
        base_slug = slugify(o.name)
        candidate_slug = base_slug
        idx = 2
        while candidate_slug in used_slugs:
            candidate_slug = f"{base_slug}-{idx}"
            idx += 1
        
        o.slug = candidate_slug
        used_slugs.add(candidate_slug)
        if not o.display_name:
            o.display_name = o.name

    db.commit()

    # 4. Verify canonical count & unique slug constraint
    final_orgs = db.query(models.Organization).all()
    print(f"\n=== CLEANUP COMPLETED ===")
    print(f"Total Canonical Organizations Remaining: {len(final_orgs)}")
    for o in final_orgs:
        u_cnt = db.query(models.User).filter(models.User.org_id == o.id).count()
        a_cnt = db.query(models.Agent).filter(models.Agent.org_id == o.id).count()
        print(f"ID: {o.id} | Slug: {o.slug!r} | Name: {o.name!r} | Users: {u_cnt} | Agents: {a_cnt}")

    db.close()

if __name__ == "__main__":
    cleanup_and_deduplicate()
