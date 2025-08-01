#!/bin/bash
set -e

# Initialize data directories
echo "🔧 Initializing Email Agent container..."

mkdir -p /app/data /app/logs /app/briefs

# Check if database exists, if not initialize it
if [ ! -f "/app/data/email_agent.db" ]; then
    echo "📊 Initializing database..."
    python -c "
from email_agent.storage.database import DatabaseManager
db = DatabaseManager()
print('✅ Database initialized')
"
fi

# If Gmail credentials are provided, set up connector
if [ -n "$GOOGLE_CLIENT_ID" ] && [ -n "$GOOGLE_CLIENT_SECRET" ]; then
    echo "📧 Setting up Gmail connector..."
    python -c "
from email_agent.storage.database import DatabaseManager
from email_agent.storage.models import ConnectorConfigORM
import os

db = DatabaseManager()
with db.get_session() as session:
    # Check if Gmail connector already exists
    existing = session.query(ConnectorConfigORM).filter_by(type='gmail').first()
    if not existing:
        connector_config = ConnectorConfigORM(
            type='gmail',
            name='Primary Gmail',
            enabled=True,
            config={
                'client_id': os.getenv('GOOGLE_CLIENT_ID'),
                'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
                'max_results': 100
            },
            sync_frequency=300,
            max_emails=1000
        )
        session.add(connector_config)
        session.commit()
        print('✅ Gmail connector configured')
    else:
        print('✅ Gmail connector already exists')
"
fi

echo "🚀 Email Agent container ready!"

# Execute the command
exec "$@"