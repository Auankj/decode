# 🍪 Cookie-Licking Detector

**An intelligent system to detect and manage stale issue claims in GitHub repositories**

> "Cookie-licking" refers to users who claim GitHub issues but never follow through, blocking others from contributing. This system automatically detects such behavior and takes corrective action.

---

## 🚀 Hackathon Demo

This project implements all features specified in the comprehensive project documentation, including:

### ✨ Key Features Implemented

- **🧠 Multi-Level Pattern Matching**: 95% confidence for direct claims, 90% for assignment requests, 70% for questions
- **🔐 Distributed Locking**: Redis-based locks prevent concurrent processing conflicts
- **⚡ Atomic Transactions**: INSERT claim + activity_log + schedule job in single transaction
- **📊 Progress Monitoring**: Tracks PRs, commits, and user activity to reset timers
- **📧 Smart Notifications**: Polite email and GitHub comment nudges using SendGrid
- **🤖 Auto-Release**: Automatically releases stale claims after grace period
- **📈 Analytics Dashboard**: Comprehensive metrics and repository insights
- **🎯 Context Analysis**: +10% confidence boost for maintainer replies

### 🏗️ Architecture Highlights

- **FastAPI** REST API with comprehensive endpoints
- **PostgreSQL** with optimized schema and indexes
- **Redis** for distributed locking and queues
- **Celery** for background job processing
- **Ecosyste.ms API** integration with 60 req/min rate limiting
- **GitHub API** integration for assignments and comments
- **SendGrid** email service integration

---

## 🎪 Quick Demo Setup

### Prerequisites
- Docker and Docker Compose
- Git

### 1. Clone Repository
```bash
git clone https://github.com/your-org/cookie-licking-detector.git
cd cookie-licking-detector
```

### 2. Environment Setup
```bash
cp .env.example .env
# Edit .env with your GitHub token, SendGrid API key, etc.
```

### 3. Start Development Environment
```bash
make dev
# OR
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### 4. Access Application
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **pgAdmin**: http://localhost:8080 (admin@example.com / admin)
- **Redis Commander**: http://localhost:8081
- **Flower (Celery)**: http://localhost:5555

### 5. Initialize Database
```bash
# Run migrations
make migrate

# Seed with demo data (optional)
make seed
```

---

## 🚀 Production Deployment

### Automated Deployment
```bash
# Configure production environment
cp .env.example .env
# Edit with production values

# Deploy with automated script
./deploy.sh deploy
```

### Manual Production Setup
```bash
# Build production images
make build-prod

# Start production environment
make prod
# OR
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Production Services
- **API**: http://your-domain.com
- **Monitoring**: http://your-domain.com:9090 (Prometheus)
- **Admin Tools**: http://your-domain.com:8080 (pgAdmin)
- **SSL**: Configured via Nginx with Let's Encrypt

---

## 🔧 Development Guide

### Common Commands

```bash
# Development environment
make dev                 # Start development environment
make dev-detach         # Start in background

# Testing
make test               # Run test suite
make test-ci            # Run CI tests with coverage

# Code quality
make lint               # Run linting checks
make format             # Format code with Black/isort
make security           # Run security scans

# Database operations
make migrate            # Run database migrations
make migrate-create     # Create new migration
make seed               # Seed with test data

# Monitoring
make logs               # View application logs
make logs-celery        # View Celery logs
make monitor            # Open monitoring interfaces

# Cleanup
make clean              # Remove containers and volumes
make clean-all          # Remove everything including images
```

### Development Workflow

1. **Start development environment**
   ```bash
   make dev
   ```

2. **Make your changes**
   - Backend code in `app/`
   - Database models in `app/db/models/`
   - API routes in `app/api/`
   - Background tasks in `app/tasks/`

3. **Test your changes**
   ```bash
   make test
   make lint
   ```

4. **Create database migrations**
   ```bash
   make migrate-create
   ```

5. **Access development tools**
   - Shell: `make shell`
   - Database: `make db-shell`
   - Redis: `make redis-shell`

---

## 🌐 Demo Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Health check |
| `GET /api/dashboard/stats` | System statistics |
| `GET /api/claims` | List all claims |
| `POST /api/repositories` | Register repository |
| `GET /docs` | Interactive API documentation |

### 🧪 Test Pattern Matching

The system includes a sophisticated pattern matching engine:

```python
# Direct Claims (95% confidence)
"I'll take this!" → ✅ CLAIM [95%]
"I can work on this" → ✅ CLAIM [95%]

# Assignment Requests (90% confidence)  
"Please assign to me" → ✅ CLAIM [90%]
"I want to work on this" → ✅ CLAIM [90%]

# Questions (70% confidence)
"Can I work on this?" → ✅ CLAIM [70%]
"Is this available?" → ✅ CLAIM [70%]

# Non-claims (below 75% threshold)
"This looks interesting" → ❌ NO CLAIM [0%]
```

---

## 📊 Demo Scenarios

The demo creates three realistic scenarios:

1. **Fresh Claim**: `eager-contributor` just claimed issue #101
2. **Stale Claim**: `slow-worker` claimed issue #102, 4 days ago (ready for nudge)
3. **Ghost Claim**: `ghost-claimer` claimed issue #103, 10 days ago (ready for auto-release)

---

## 🛠️ Technical Implementation

### Database Schema (from MD specs)
- **repositories**: Monitoring configuration
- **issues**: GitHub issue data
- **claims**: Claim records with confidence scores
- **activity_log**: System activity tracking
- **progress_tracking**: PR and commit monitoring
- **queue_jobs**: Background job management

### Pattern Matching Engine
```python
# Exact confidence scores from MD file
DIRECT_CLAIM = 95%      # "I'll take this"
ASSIGNMENT_REQUEST = 90% # "Please assign to me"  
QUESTION = 70%          # "Can I work on this?"
PROGRESS_UPDATE = 0%    # For timer reset only

# Context analysis
+10% for maintainer replies
+5% for already assigned users
Threshold: 75% (configurable)
```

### Queue System
- **comment_analysis**: Process new comments for claims
- **nudge_check**: Send notifications to inactive users
- **progress_check**: Monitor PRs and commits
- **auto_release_check**: Release stale claims
- **dead_letter**: Failed jobs for manual review

### API Design (exact MD specs)
- Repository Management: CRUD operations
- Claim Management: List, details, manual actions
- Dashboard: Stats, metrics, user insights
- Progress Tracking: PR/commit monitoring

---

## 🎯 Hackathon Success Criteria

✅ **Complete MVP**: All core features implemented  
✅ **Pattern Matching**: Multi-level detection with exact confidence scores  
✅ **Distributed System**: Redis locking, atomic transactions  
✅ **Real Integration**: Ecosyste.ms API, GitHub API, SendGrid  
✅ **Comprehensive Testing**: Demo scenarios and test data  
✅ **Production Ready**: Error handling, logging, monitoring  
✅ **Documentation**: Complete API docs and architecture  

---

## 🔮 Future Enhancements

- **Machine Learning**: Train models on pattern matching data
- **GitHub App**: Real-time webhook integration
- **Advanced Analytics**: Predictive completion likelihood
- **Slack Integration**: Team notifications
- **Mobile Dashboard**: React Native app

---

## 📚 Architecture Deep Dive

This implementation follows the exact specifications from the comprehensive project documentation:

- **Event Ingestion**: Webhooks and API polling
- **Processing Pipeline**: Multi-queue job routing
- **Comment Analysis**: Pattern matching with confidence scoring
- **Distributed Locking**: Redis-based concurrency control
- **Progress Monitoring**: PR/commit activity tracking
- **Notification System**: Email and GitHub comments
- **Auto-Release**: Configurable grace periods
- **Analytics**: Repository and user metrics

---

## 🏆 Demonstration Ready

The system is fully functional and ready for live demonstration:

1. **Pattern Detection**: Real-time comment analysis
2. **Claim Management**: Full lifecycle tracking
3. **Dashboard Insights**: Live metrics and analytics
4. **API Integration**: Working Ecosyste.ms connection
5. **Background Jobs**: Celery queue processing
6. **Data Persistence**: PostgreSQL with sample data

**This is a complete, production-ready implementation of the Cookie-Licking Detector system as specified in the project documentation.**