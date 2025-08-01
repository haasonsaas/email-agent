#!/bin/bash

# Email Agent Docker Runner
set -e

echo "🐳 Building Email Agent Docker container..."
docker-compose build

echo "🚀 Starting Email Agent..."
docker-compose up -d

echo "📊 Container status:"
docker-compose ps

echo ""
echo "🎯 Usage Examples:"
echo "  # Enter container for interactive use"
echo "  docker-compose exec email-agent bash"
echo ""
echo "  # Run commands directly"
echo "  docker-compose exec email-agent email-agent --help"
echo "  docker-compose exec email-agent email-agent init"
echo "  docker-compose exec email-agent email-agent sync --since '1 day ago'"
echo "  docker-compose exec email-agent email-agent stats"
echo "  docker-compose exec email-agent email-agent dashboard"
echo ""
echo "  # View logs"
echo "  docker-compose logs -f email-agent"
echo ""
echo "  # Stop container"
echo "  docker-compose down"
echo ""
echo "✨ Don't forget to:"
echo "  1. Add your OpenAI API key to .env"
echo "  2. Copy your Gmail OAuth credentials as client_secret.json"
echo "  3. Run 'email-agent init' inside the container first"
