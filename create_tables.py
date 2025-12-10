#!/usr/bin/env python3
"""
Script to create database tables
"""
import sys
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env file")
    sys.exit(1)

print(f"📊 Connecting to database...")

try:
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # Import Base and models
    from database import Base
    import models
    
    # Create all tables
    print("🔨 Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database tables created successfully!")
    print(f"📝 Tables created: {', '.join(Base.metadata.tables.keys())}")
    
except Exception as e:
    print(f"❌ Error creating tables: {e}")
    sys.exit(1)
