# Educational Consultant Bot - Deployment Guide

## Overview

This guide covers the deployment of the updated Educational Consultant Bot with SQLite database persistence, conversation history, and enhanced educational program guidance capabilities.

## New Features in This Version

### 🗄️ Database Persistence
- **SQLite Database**: Conversation history is now stored persistently
- **Volume Mounting**: Database survives container restarts
- **Automatic Initialization**: Database schema is created automatically
- **Migration Support**: Safe database schema updates

### 🎓 Educational Consultant
- **ITMO Focus**: Specialized knowledge about ITMO University programs
- **Conversation Context**: Maintains conversation history for better responses
- **Three-Phase Context**: Combines conversation history, RAG results, and educational programs
- **History Command**: Users can view their conversation history with `/history`

### 🔧 Infrastructure Improvements
- **Health Checks**: Container health monitoring
- **Database Scripts**: Initialization and migration utilities
- **Comprehensive Testing**: Full integration test suite
- **Enhanced Logging**: Better error tracking and performance monitoring

## Prerequisites

### Required Services
- **Qdrant Vector Database**: Running on `localhost:6333`
- **Ollama LLM Service**: Running on `host.orb.internal:11434`
- **Docker & Docker Compose**: For containerization

### Required Models in Ollama
```bash
# Embedding model
ollama pull dengcao/Qwen3-Embedding-0.6B:Q8_0

# Reranker model  
ollama pull dengcao/Qwen3-Reranker-4B:Q4_K_M

# Generation model
ollama pull qwen3:4b
```

### Environment Variables
Create a `.env` file in the bot directory:
```env
# Required
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Optional (defaults provided)
DATABASE_PATH=/app/data/conversations.db
LOG_LEVEL=INFO
```

## Deployment Steps

### 1. Pre-Deployment Checks

Verify external services are running:
```bash
# Check Qdrant
curl -f http://localhost:6333/health || echo "Qdrant not ready"

# Check Ollama
curl -f http://host.orb.internal:11434/api/version || echo "Ollama not ready"
```

### 2. Database Initialization

The database will be automatically initialized when the container starts. You can also run initialization manually:

```bash
# Manual database initialization
python init_db.py

# Check database status
python -c "
from init_db import DatabaseInitializer
db = DatabaseInitializer('/app/data/conversations.db')
print(db.get_database_info())
"
```

### 3. Build and Deploy

```bash
# Build the container
docker-compose build

# Start the services
docker-compose up -d

# Check container health
docker-compose ps
docker-compose logs bot
```

### 4. Verify Deployment

```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs -f bot

# Check database health
docker-compose exec bot python -c "
from services.conversation_service import ConversationService
cs = ConversationService('/app/data/conversations.db')
print('Database healthy:', cs.health_check())
print('Service info:', cs.get_service_info())
"
```

### 5. Run Integration Tests

```bash
# Run comprehensive integration tests
docker-compose exec bot python test_full_integration.py

# Run specific component tests
docker-compose exec bot python test_conversation_service.py
docker-compose exec bot python test_educational_consultant.py
```

## Database Management

### Database Location
- **Container Path**: `/app/data/conversations.db`
- **Volume**: `bot_data` (persistent across container restarts)
- **Host Access**: Data persists in Docker volume

### Database Operations

```bash
# Initialize database
docker-compose exec bot python init_db.py

# Run migrations
docker-compose exec bot python migrate_db.py

# Check database info
docker-compose exec bot python -c "
from services.conversation_service import ConversationService
cs = ConversationService('/app/data/conversations.db')
print(cs.get_service_info())
"
```

### Backup and Restore

```bash
# Create backup
docker-compose exec bot python -c "
from migrate_db import DatabaseMigrator
dm = DatabaseMigrator('/app/data/conversations.db')
backup_path = dm.create_backup()
print(f'Backup created: {backup_path}')
"

# List backups
docker-compose exec bot ls -la /app/data/*.backup_*
```

## Configuration

### Docker Compose Configuration

The `docker-compose.yml` includes:
- **Volume Mounting**: `bot_data:/app/data` for database persistence
- **Health Checks**: Container health monitoring
- **Environment Variables**: Database path configuration
- **Service Dependencies**: Waits for Qdrant and Ollama

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | *required* | Telegram bot token |
| `DATABASE_PATH` | `/app/data/conversations.db` | SQLite database path |
| `QDRANT_HOST` | `localhost` | Qdrant server host |
| `QDRANT_PORT` | `6333` | Qdrant server port |
| `OLLAMA_HOST` | `host.orb.internal` | Ollama server host |
| `OLLAMA_PORT` | `11434` | Ollama server port |
| `LOG_LEVEL` | `INFO` | Logging level |

## Bot Commands

### Available Commands
- `/start` - Initialize bot and show welcome message
- `/help` - Show help information
- `/history` - Show recent conversation history

### Usage Examples

```
User: /start
Bot: Добро пожаловать! Я образовательный консультант ИТМО...

User: Расскажи о магистратуре по ИИ
Bot: [Provides detailed information about AI master's program]

User: /history
Bot: [Shows recent conversation exchanges]
```

## Monitoring and Troubleshooting

### Health Checks

The container includes health checks that verify:
- Database connectivity
- Conversation service functionality
- Overall system health

```bash
# Check health status
docker-compose ps
docker inspect $(docker-compose ps -q bot) | grep -A 5 Health
```

### Log Analysis

```bash
# View real-time logs
docker-compose logs -f bot

# Search for errors
docker-compose logs bot | grep ERROR

# Check database operations
docker-compose logs bot | grep -i database
```

### Common Issues

#### Database Connection Issues
```bash
# Check database file permissions
docker-compose exec bot ls -la /app/data/

# Verify database initialization
docker-compose exec bot python init_db.py
```

#### Memory Issues
```bash
# Check container resource usage
docker stats $(docker-compose ps -q bot)

# Check database size
docker-compose exec bot du -h /app/data/conversations.db
```

#### Service Dependencies
```bash
# Verify external services
curl -f http://localhost:6333/health
curl -f http://host.orb.internal:11434/api/version
```

## Performance Optimization

### Database Optimization
- **Indexing**: Automatic indexes on user_id and timestamp
- **Cleanup**: Built-in old conversation cleanup
- **Connection Pooling**: Efficient SQLite connection management

### Memory Management
- **Conversation Limits**: Configurable conversation history limits
- **Context Truncation**: Automatic context size management
- **Resource Monitoring**: Built-in performance logging

## Security Considerations

### Database Security
- **Local Storage**: Database stored in Docker volume
- **No External Access**: Database not exposed outside container
- **Input Sanitization**: All user inputs are sanitized

### Bot Security
- **Token Protection**: Bot token stored in environment variables
- **Rate Limiting**: Built-in Telegram rate limiting
- **Error Handling**: Secure error messages without sensitive data

## Maintenance

### Regular Tasks

```bash
# Update container
docker-compose pull
docker-compose up -d

# Clean old backups (keeps 5 most recent)
docker-compose exec bot python -c "
from migrate_db import DatabaseMigrator
dm = DatabaseMigrator('/app/data/conversations.db')
dm.cleanup_old_backups()
"

# Check database health
docker-compose exec bot python -c "
from services.conversation_service import ConversationService
cs = ConversationService('/app/data/conversations.db')
print('Health:', cs.health_check())
print('Stats:', cs.get_service_info())
"
```

### Database Maintenance

```bash
# Clean old conversations (older than 30 days)
docker-compose exec bot python -c "
from services.conversation_service import ConversationService
cs = ConversationService('/app/data/conversations.db')
deleted = cs.cleanup_old_conversations(days_to_keep=30)
print(f'Deleted {deleted} old conversations')
"
```

## Rollback Procedures

### Container Rollback
```bash
# Stop current version
docker-compose down

# Restore previous image
docker-compose up -d --force-recreate
```

### Database Rollback
```bash
# List available backups
docker-compose exec bot ls -la /app/data/*.backup_*

# Restore from backup
docker-compose exec bot python -c "
from migrate_db import DatabaseMigrator
dm = DatabaseMigrator('/app/data/conversations.db')
success = dm.restore_backup('/app/data/conversations.db.backup_YYYYMMDD_HHMMSS')
print('Restore success:', success)
"
```

## Support and Debugging

### Debug Mode
```bash
# Run with debug logging
docker-compose exec bot env LOG_LEVEL=DEBUG python bot.py
```

### Database Inspection
```bash
# Connect to database
docker-compose exec bot sqlite3 /app/data/conversations.db

# Common queries
.tables
.schema conversations
SELECT COUNT(*) FROM conversations;
SELECT user_id, COUNT(*) FROM conversations GROUP BY user_id;
```

### Integration Testing
```bash
# Run full test suite
docker-compose exec bot python test_full_integration.py

# Test specific components
docker-compose exec bot python test_conversation_service.py
```

## Version Information

- **Bot Version**: Educational Consultant v2.0
- **Database Schema**: Version 1
- **Python Version**: 3.11
- **Key Dependencies**: 
  - python-telegram-bot >= 22.3
  - qdrant-client >= 1.15.1
  - langchain >= 0.3.27

---

For additional support or questions, check the logs and run the integration tests to identify specific issues.