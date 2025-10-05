#!/usr/bin/env python3
"""
Script to fix all API route files to use proper async database connections
"""
import os
import re

def fix_route_file(filepath):
    """Fix a single route file"""
    print(f"Fixing {filepath}...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Replace imports
    content = re.sub(
        r'from app\.models import.*',
        'from app.db.database import get_async_session\nfrom app.db.models import Repository, Issue, Claim, User',
        content
    )
    
    # Replace Session with AsyncSession
    content = re.sub(
        r'from sqlalchemy\.orm import Session',
        'from sqlalchemy.ext.asyncio import AsyncSession\nfrom sqlalchemy import select',
        content
    )
    
    # Replace db dependency
    content = re.sub(
        r'db: Session = Depends\(get_db\)',
        'db: AsyncSession = Depends(get_async_session)',
        content
    )
    
    # Replace query patterns
    content = re.sub(
        r'db\.query\((\w+)\)',
        r'select(\1)',
        content
    )
    
    # Replace filter patterns
    content = re.sub(
        r'\.filter\(([^)]+)\)',
        r'.where(\1)',
        content
    )
    
    # Replace .first() patterns
    content = re.sub(
        r'(\w+)\.first\(\)',
        r'(await db.execute(\1)).scalar_one_or_none()',
        content
    )
    
    # Replace .all() patterns
    content = re.sub(
        r'(\w+)\.all\(\)',
        r'(await db.execute(\1)).scalars().all()',
        content
    )
    
    # Replace db.commit()
    content = re.sub(r'db\.commit\(\)', r'await db.commit()', content)
    content = re.sub(r'db\.rollback\(\)', r'await db.rollback()', content)
    content = re.sub(r'db\.refresh\(([^)]+)\)', r'await db.refresh(\1)', content)
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"Fixed {filepath}")

if __name__ == "__main__":
    api_dir = "app/api"
    route_files = [
        "claim_routes.py", 
        "dashboard_routes.py", 
        "webhook_routes.py",
        "progress_routes.py"
    ]
    
    for route_file in route_files:
        filepath = os.path.join(api_dir, route_file)
        if os.path.exists(filepath):
            fix_route_file(filepath)