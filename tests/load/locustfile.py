"""
Load testing script for Cookie Licking Detector using Locust.
"""

import json
import random
import uuid
from locust import HttpUser, task, between, events
from locust.exception import RescheduleTask


class AuthenticatedUser(HttpUser):
    """Base user class with authentication."""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login user and get token."""
        self.token = None
        self.user_id = None
        
        # Register or login user
        user_email = f"loadtest_{uuid.uuid4().hex[:8]}@example.com"
        user_data = {
            "email": user_email,
            "password": "LoadTest123!",
            "full_name": f"Load Test User {random.randint(1, 1000)}"
        }
        
        # Try to register
        response = self.client.post("/api/v1/auth/register", json=user_data)
        
        if response.status_code not in [201, 400]:  # 400 if user exists
            print(f"Registration failed: {response.text}")
            raise RescheduleTask()
        
        # Login
        login_data = {
            "email": user_email,
            "password": "LoadTest123!"
        }
        
        response = self.client.post("/api/v1/auth/login", json=login_data)
        
        if response.status_code != 200:
            print(f"Login failed: {response.text}")
            raise RescheduleTask()
        
        token_data = response.json()
        self.token = token_data["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def on_stop(self):
        """Logout user."""
        if self.token:
            self.client.post("/api/v1/auth/logout", headers=self.headers)


class APIUser(AuthenticatedUser):
    """User that tests main API endpoints."""
    
    @task(3)
    def get_health(self):
        """Test health endpoint."""
        self.client.get("/health")
    
    @task(2)
    def get_user_profile(self):
        """Test getting user profile."""
        if not self.token:
            return
        
        self.client.get("/api/v1/auth/me", headers=self.headers)
    
    @task(5)
    def list_repositories(self):
        """Test listing repositories."""
        if not self.token:
            return
        
        params = {
            "page": random.randint(1, 3),
            "per_page": random.choice([10, 20, 50])
        }
        
        self.client.get("/api/v1/repositories", params=params, headers=self.headers)
    
    @task(4)
    def list_claims(self):
        """Test listing claims."""
        if not self.token:
            return
        
        params = {
            "page": random.randint(1, 3),
            "per_page": random.choice([10, 20, 50]),
            "status": random.choice(["active", "released", "all"])
        }
        
        self.client.get("/api/v1/claims", params=params, headers=self.headers)
    
    @task(2)
    def get_analytics(self):
        """Test analytics endpoints."""
        if not self.token:
            return
        
        endpoints = [
            "/api/v1/analytics/dashboard",
            "/api/v1/analytics/claims/stats",
            "/api/v1/analytics/repositories/stats"
        ]
        
        endpoint = random.choice(endpoints)
        self.client.get(endpoint, headers=self.headers)
    
    @task(1)
    def create_api_key(self):
        """Test API key creation."""
        if not self.token:
            return
        
        key_data = {
            "name": f"Load Test Key {random.randint(1, 1000)}",
            "description": "API key created during load testing",
            "scopes": random.sample(
                ["repo:read", "claims:read", "analytics:read"], 
                random.randint(1, 3)
            )
        }
        
        response = self.client.post("/api/v1/auth/api-keys", json=key_data, headers=self.headers)
        
        # If successful, try to delete the key to clean up
        if response.status_code == 201:
            key_id = response.json()["id"]
            self.client.delete(f"/api/v1/auth/api-keys/{key_id}", headers=self.headers)


class WebhookUser(HttpUser):
    """User that simulates GitHub webhooks."""
    
    wait_time = between(0.5, 2)
    
    def on_start(self):
        """Setup webhook data."""
        self.webhook_secret = "test_webhook_secret"
        self.repositories = [
            "owner1/repo1",
            "owner2/repo2", 
            "owner3/repo3"
        ]
    
    @task
    def send_issue_comment_webhook(self):
        """Send issue comment webhook."""
        repo = random.choice(self.repositories)
        owner, repo_name = repo.split("/")
        
        payload = {
            "action": "created",
            "issue": {
                "id": random.randint(1, 1000),
                "number": random.randint(1, 500),
                "title": f"Test Issue {random.randint(1, 100)}",
                "body": "This is a test issue for load testing",
                "state": "open",
                "user": {
                    "login": f"user{random.randint(1, 100)}",
                    "id": random.randint(1000, 9999)
                },
                "assignees": [],
                "labels": []
            },
            "comment": {
                "id": random.randint(1000, 9999),
                "body": random.choice([
                    "I'll take this issue!",
                    "I want to work on this",
                    "Can I work on this issue?",
                    "This looks interesting, I'd like to contribute",
                    "I'll handle this one"
                ]),
                "user": {
                    "login": f"contributor{random.randint(1, 50)}",
                    "id": random.randint(10000, 99999)
                },
                "created_at": "2024-01-01T12:00:00Z"
            },
            "repository": {
                "id": random.randint(100000, 999999),
                "full_name": repo,
                "name": repo_name,
                "owner": {
                    "login": owner,
                    "id": random.randint(1000, 9999)
                }
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-GitHub-Event": "issue_comment",
            "X-GitHub-Delivery": str(uuid.uuid4()),
            "X-Hub-Signature-256": "sha256=test_signature"  # Simplified for load testing
        }
        
        self.client.post("/api/v1/webhooks/github", json=payload, headers=headers)


class AdminUser(AuthenticatedUser):
    """Admin user for testing admin endpoints."""
    
    weight = 1  # Lower weight - fewer admin users
    
    def on_start(self):
        """Create admin user."""
        # Try to create admin user
        admin_email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
        user_data = {
            "email": admin_email,
            "password": "AdminTest123!",
            "full_name": "Load Test Admin",
            "roles": ["admin"]
        }
        
        self.client.post("/api/v1/auth/register", json=user_data)
        
        # Login
        login_data = {
            "email": admin_email,
            "password": "AdminTest123!"
        }
        
        response = self.client.post("/api/v1/auth/login", json=login_data)
        
        if response.status_code == 200:
            token_data = response.json()
            self.token = token_data["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            raise RescheduleTask()
    
    @task(2)
    def list_all_users(self):
        """Test admin endpoint to list users."""
        if not self.token:
            return
        
        params = {
            "page": random.randint(1, 3),
            "per_page": 20
        }
        
        self.client.get("/api/v1/admin/users", params=params, headers=self.headers)
    
    @task(1)
    def get_system_stats(self):
        """Test admin system statistics."""
        if not self.token:
            return
        
        self.client.get("/api/v1/admin/stats", headers=self.headers)
    
    @task(1)
    def manage_repositories(self):
        """Test admin repository management."""
        if not self.token:
            return
        
        # List repositories with admin privileges
        self.client.get("/api/v1/admin/repositories", headers=self.headers)


class DatabaseStressUser(AuthenticatedUser):
    """User that creates database stress through complex queries."""
    
    weight = 2
    
    @task(3)
    def complex_analytics_query(self):
        """Test complex analytics queries."""
        if not self.token:
            return
        
        params = {
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "group_by": random.choice(["day", "week", "month"]),
            "include_details": "true"
        }
        
        self.client.get("/api/v1/analytics/trends", params=params, headers=self.headers)
    
    @task(2) 
    def search_claims(self):
        """Test claim search functionality."""
        if not self.token:
            return
        
        search_terms = [
            "python", "javascript", "bug", "feature", "help wanted",
            "good first issue", "documentation", "test", "api"
        ]
        
        params = {
            "query": random.choice(search_terms),
            "page": random.randint(1, 5),
            "per_page": random.choice([20, 50, 100])
        }
        
        self.client.get("/api/v1/claims/search", params=params, headers=self.headers)
    
    @task(1)
    def bulk_operations(self):
        """Test bulk operations."""
        if not self.token:
            return
        
        # Simulate bulk claim processing
        claim_ids = [random.randint(1, 1000) for _ in range(random.randint(5, 20))]
        
        bulk_data = {
            "claim_ids": claim_ids,
            "action": random.choice(["release", "nudge", "assign"])
        }
        
        self.client.post("/api/v1/claims/bulk", json=bulk_data, headers=self.headers)


# Event handlers for monitoring
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, start_time, url, **kwargs):
    """Log slow requests."""
    if response_time > 2000:  # Log requests slower than 2 seconds
        print(f"Slow request: {request_type} {name} - {response_time}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Print test start information."""
    print("Load test started")
    print(f"Target host: {environment.host}")
    print(f"Users: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'N/A'}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print test completion information."""
    print("Load test completed")
    
    # Print summary statistics
    stats = environment.runner.stats
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Failed requests: {stats.total.num_failures}")
    print(f"Median response time: {stats.total.median_response_time}ms")
    print(f"95th percentile: {stats.total.get_response_time_percentile(0.95)}ms")
    print(f"Requests per second: {stats.total.current_rps:.2f}")


# Custom test scenarios for specific load patterns
class BurstTrafficUser(HttpUser):
    """Simulates burst traffic patterns."""
    
    weight = 1
    wait_time = between(0.1, 0.5)  # Very short wait time for burst
    
    @task
    def rapid_health_checks(self):
        """Rapid health check requests."""
        self.client.get("/health")
    
    @task
    def rapid_api_calls(self):
        """Rapid API calls to test rate limiting."""
        endpoints = [
            "/api/v1/repositories", 
            "/api/v1/claims",
            "/health"
        ]
        
        endpoint = random.choice(endpoints)
        self.client.get(endpoint)


# Configuration for different load testing scenarios
class LoadTestConfig:
    """Configuration for different load testing scenarios."""
    
    # Light load testing
    LIGHT_LOAD = {
        "users": 10,
        "spawn_rate": 2,
        "run_time": "5m"
    }
    
    # Medium load testing  
    MEDIUM_LOAD = {
        "users": 50,
        "spawn_rate": 5,
        "run_time": "10m"
    }
    
    # Heavy load testing
    HEAVY_LOAD = {
        "users": 100,
        "spawn_rate": 10,
        "run_time": "15m"
    }
    
    # Spike testing
    SPIKE_LOAD = {
        "users": 200,
        "spawn_rate": 20,
        "run_time": "5m"
    }


if __name__ == "__main__":
    print("Load testing configuration:")
    print("- Light load: locust -f locustfile.py --users 10 --spawn-rate 2 -t 5m")
    print("- Medium load: locust -f locustfile.py --users 50 --spawn-rate 5 -t 10m") 
    print("- Heavy load: locust -f locustfile.py --users 100 --spawn-rate 10 -t 15m")
    print("- Spike test: locust -f locustfile.py --users 200 --spawn-rate 20 -t 5m")