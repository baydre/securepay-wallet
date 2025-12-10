#!/bin/bash

# SecurePay Wallet Setup Script

echo "🚀 Setting up SecurePay Wallet..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚙️ Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️ Please update .env with your actual credentials!"
else
    echo "✅ .env file already exists"
fi

# Create database tables
echo "🗄️ Creating database tables..."
python -c "from database import engine, Base; import models; Base.metadata.create_all(bind=engine)" 2>/dev/null || echo "⚠️ Database connection failed. Please ensure PostgreSQL is running and .env is configured."

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update .env with your actual credentials"
echo "2. Ensure PostgreSQL is running"
echo "3. Run: uvicorn main:app --reload"
echo ""
echo "API will be available at: http://localhost:8000"
echo "Documentation: http://localhost:8000/docs"
