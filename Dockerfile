# Email Agent Docker Container
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash email-agent

# Set working directory
WORKDIR /app

# Copy all source files first
COPY . ./

# Make entrypoint executable
RUN chmod +x docker-entrypoint.sh

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel
RUN pip install -e .

# Create necessary directories
RUN mkdir -p /app/data /app/logs /app/briefs

# Set proper ownership
RUN chown -R email-agent:email-agent /app

# Switch to non-root user
USER email-agent

# Expose port (if needed for future web interface)
EXPOSE 8080

# Set environment variables for runtime
ENV DATABASE_URL=sqlite:////app/data/email_agent.db
ENV LOG_FILE=/app/logs/agent.log
ENV BRIEF_OUTPUT_DIR=/app/briefs
ENV PYTHONPATH=/app/src

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD email-agent init check || exit 1

# Set entrypoint
ENTRYPOINT ["./docker-entrypoint.sh"]

# Default command
CMD ["bash"]
