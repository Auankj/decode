# 🍪 Cookie Licking Detector API - Complete Documentation

## 🎯 Overview
The Cookie Licking Detector API is an enterprise-grade platform for detecting and managing stale issue claims in GitHub repositories. It features comprehensive Swagger UI documentation with interactive testing capabilities.

## 📖 Access API Documentation

### 🚀 Quick Start
```bash
# Start the server
cd /Users/abhra/Desktop/decode/cookie-licking-detector
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Access documentation
open http://localhost:8000/docs    # Swagger UI
open http://localhost:8000/redoc   # ReDoc format
```

### 📋 Documentation URLs
- **Swagger UI**: `http://localhost:8000/docs` - Interactive API documentation
- **ReDoc**: `http://localhost:8000/redoc` - Clean, readable documentation
- **OpenAPI Spec**: `http://localhost:8000/openapi.json` - Machine-readable API specification
- **API Root**: `http://localhost:8000/` - Basic API information

## 🎨 Enhanced Swagger UI Features

### ✨ Professional Features Implemented
- **Rich Markdown Documentation**: Comprehensive descriptions with formatting, code examples, and usage guides
- **Organized by Tags**: Endpoints grouped by functionality (authentication, repositories, claims, etc.)
- **Interactive Testing**: Test all endpoints directly from the documentation interface
- **Request/Response Examples**: Real-world examples for all endpoints
- **Professional Branding**: Custom styling with contact information and licensing
- **Multiple Formats**: Both Swagger UI and ReDoc for different preferences
- **Enhanced UI Configuration**: Deep linking, syntax highlighting, request duration tracking

### 🏷️ API Endpoint Organization (45+ endpoints)

#### 🔐 Authentication (`/api/v1/auth/`)
**22 endpoints** for complete user management:
- User registration and login
- JWT token management (create, refresh, revoke)
- API key management
- User profile operations
- Admin user management
- Password reset functionality

#### 🗂️ Repositories (`/api/v1/repositories/`)
**4 endpoints** for repository management:
- Add and configure GitHub repositories
- Update repository settings
- List monitored repositories
- Remove repositories from monitoring

#### 📋 Claims (`/api/v1/claims/`)
**5 endpoints** for claim tracking:
- List active and historical claims
- Get detailed claim information
- View claim activity logs
- Manual claim management
- Claim analytics and insights

#### 📊 Dashboard (`/api/v1/dashboard/`)
**4 endpoints** for analytics and insights:
- Repository activity summaries
- System-wide statistics
- Performance metrics
- Admin analytics dashboard

#### 🎣 Webhooks (`/api/v1/webhooks/`)
**6 endpoints** for GitHub integration:
- GitHub webhook event processing
- Webhook configuration management
- Event history and logs
- Integration testing endpoints

#### 🛠️ System (`/`)
**4 endpoints** for system operations:
- Health checks with detailed component status
- Prometheus metrics for monitoring
- Version and build information
- API root information

## 🔍 Key Documentation Features

### 📚 Comprehensive Endpoint Documentation
Each endpoint includes:
- **Detailed descriptions** with markdown formatting
- **Use case examples** and best practices
- **Request/response schemas** with validation rules
- **HTTP status codes** with explanations
- **Authentication requirements** clearly marked
- **Rate limiting information** where applicable

### 🎯 Example Documentation Highlights

#### Health Check Endpoint
```
GET /health
```
- **Comprehensive system validation** (database, Redis, external APIs)
- **Detailed response examples** for healthy and unhealthy states
- **Integration guidance** for monitoring systems
- **Response time metrics** and performance indicators

#### Authentication Flow
```
POST /api/v1/auth/login
```
- **JWT token-based authentication** with automatic expiration
- **Secure password handling** with bcrypt hashing
- **Rate limiting protection** against brute force attacks
- **Clear error responses** for invalid credentials

### 🛡️ Security Documentation
- **JWT Authentication**: Bearer token requirements clearly documented
- **Rate Limiting**: Request limits and headers explained
- **CORS Configuration**: Cross-origin request handling
- **Security Headers**: Comprehensive security header implementation

### 📊 Monitoring and Observability
- **Prometheus Metrics**: Detailed metrics documentation at `/metrics`
- **Health Checks**: Multi-component health validation at `/health`
- **Request Tracking**: Automatic request/response logging and metrics
- **Error Handling**: Structured error responses with timestamps

## 🚀 Using the API Documentation

### 1. **Interactive Testing**
The Swagger UI provides a "Try it out" feature for every endpoint:
- Fill in parameters directly in the UI
- Execute real API calls
- View formatted responses
- Test authentication flows

### 2. **Code Generation**
Use the OpenAPI specification to generate client libraries:
```bash
# Download the OpenAPI spec
curl http://localhost:8000/openapi.json > api-spec.json

# Generate client code (various languages supported)
openapi-generator-cli generate -i api-spec.json -g python -o ./client
```

### 3. **Authentication Setup**
For protected endpoints:
1. Use `/api/v1/auth/login` to get a JWT token
2. Click "Authorize" in Swagger UI
3. Enter `Bearer <your-token>` in the authorization field
4. All subsequent requests will include the token

### 4. **Webhook Integration**
Set up GitHub webhooks pointing to:
```
POST http://your-domain.com/api/v1/webhooks/github
```

## 🔧 Development and Integration

### API Client Setup
```python
import httpx

# Basic API client
client = httpx.Client(base_url="http://localhost:8000")

# Authentication
login_response = client.post("/api/v1/auth/login", json={
    "username": "your-username",
    "password": "your-password"
})
token = login_response.json()["access_token"]

# Authenticated requests
headers = {"Authorization": f"Bearer {token}"}
response = client.get("/api/v1/claims", headers=headers)
```

### Webhook Integration
```python
# GitHub webhook handler example
@app.post("/webhook")
async def github_webhook(request: Request):
    payload = await request.json()
    # Forward to Cookie Licking Detector
    response = httpx.post("http://localhost:8000/api/v1/webhooks/github", json=payload)
    return response.json()
```

## 📈 Production Deployment

### Environment Configuration
```bash
# Required environment variables
GITHUB_TOKEN=ghp_your_github_token
SENDGRID_API_KEY=SG.your_sendgrid_key
DATABASE_URL=postgresql://user:pass@localhost:5432/cookie_detector
REDIS_URL=redis://localhost:6379/0

# Optional production settings
ENVIRONMENT=production
DEBUG=false
ENABLE_METRICS=true
```

### Docker Deployment
```dockerfile
# Use the provided Dockerfile
docker build -t cookie-licking-detector .
docker run -p 8000:8000 --env-file .env cookie-licking-detector
```

## 🎉 Summary

The Cookie Licking Detector API now features **enterprise-grade Swagger UI documentation** with:

✅ **45+ documented endpoints** across 6 functional areas  
✅ **Interactive testing interface** with real-time API calls  
✅ **Professional presentation** with branding and contact info  
✅ **Comprehensive examples** and usage guidance  
✅ **Multiple documentation formats** (Swagger UI + ReDoc)  
✅ **Production-ready features** including monitoring and security  

**Access the documentation at**: `http://localhost:8000/docs`

The API is now fully documented, tested, and ready for production use! 🚀