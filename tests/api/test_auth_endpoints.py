"""
API integration tests for authentication endpoints.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import create_auth_headers, create_api_key_headers


@pytest.mark.api
@pytest.mark.asyncio
class TestAuthEndpoints:
    """Test authentication API endpoints."""

    async def test_register_user_success(self, async_client: AsyncClient):
        """Test successful user registration."""
        user_data = {
            "email": "newuser@example.com",
            "password": "StrongPassword123!",
            "full_name": "New Test User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["full_name"] == "New Test User"
        assert data["is_active"] is True
        assert "password_hash" not in data  # Should not expose password hash

    async def test_register_user_weak_password(self, async_client: AsyncClient):
        """Test user registration with weak password."""
        user_data = {
            "email": "newuser@example.com",
            "password": "weak",
            "full_name": "New Test User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "password does not meet requirements" in data["detail"]["message"].lower()

    async def test_register_user_duplicate_email(self, async_client: AsyncClient, test_user):
        """Test user registration with duplicate email."""
        user_data = {
            "email": test_user.email,  # Same email as existing user
            "password": "StrongPassword123!",
            "full_name": "Duplicate User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "already exists" in data["detail"].lower()

    async def test_login_success(self, async_client: AsyncClient, test_user):
        """Test successful user login."""
        login_data = {
            "email": test_user.email,
            "password": "TestPassword123!"
        }
        
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    async def test_login_wrong_password(self, async_client: AsyncClient, test_user):
        """Test login with wrong password."""
        login_data = {
            "email": test_user.email,
            "password": "WrongPassword123!"
        }
        
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "invalid credentials" in data["detail"].lower()

    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        """Test login with nonexistent user."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "AnyPassword123!"
        }
        
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        data = response.json()
        assert "invalid credentials" in data["detail"].lower()

    async def test_refresh_token_success(self, async_client: AsyncClient, test_user):
        """Test successful token refresh."""
        # First login to get tokens
        login_data = {
            "email": test_user.email,
            "password": "TestPassword123!"
        }
        
        login_response = await async_client.post("/api/v1/auth/login", json=login_data)
        login_data = login_response.json()
        refresh_token = login_data["refresh_token"]
        
        # Use refresh token to get new access token
        refresh_data = {
            "refresh_token": refresh_token
        }
        
        response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_refresh_token_invalid(self, async_client: AsyncClient):
        """Test token refresh with invalid token."""
        refresh_data = {
            "refresh_token": "invalid_token"
        }
        
        response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 401

    async def test_get_current_user_success(self, async_client: AsyncClient, test_user, user_token):
        """Test getting current user info."""
        headers = create_auth_headers(user_token)
        
        response = await async_client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert data["full_name"] == test_user.full_name
        assert "password_hash" not in data

    async def test_get_current_user_unauthorized(self, async_client: AsyncClient):
        """Test getting current user without authorization."""
        response = await async_client.get("/api/v1/auth/me")
        
        assert response.status_code == 401

    async def test_get_current_user_invalid_token(self, async_client: AsyncClient):
        """Test getting current user with invalid token."""
        headers = create_auth_headers("invalid_token")
        
        response = await async_client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 401

    async def test_logout_success(self, async_client: AsyncClient, test_user, user_token):
        """Test successful user logout."""
        headers = create_auth_headers(user_token)
        
        response = await async_client.post("/api/v1/auth/logout", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "logged out" in data["message"].lower()

    async def test_logout_unauthorized(self, async_client: AsyncClient):
        """Test logout without authorization."""
        response = await async_client.post("/api/v1/auth/logout")
        
        assert response.status_code == 401


@pytest.mark.api
@pytest.mark.asyncio
class TestAPIKeyEndpoints:
    """Test API key management endpoints."""

    async def test_create_api_key_success(self, async_client: AsyncClient, test_user, user_token):
        """Test successful API key creation."""
        headers = create_auth_headers(user_token)
        
        key_data = {
            "name": "Test API Key",
            "description": "API key for testing",
            "scopes": ["repo:read", "claims:read"]
        }
        
        response = await async_client.post("/api/v1/auth/api-keys", json=key_data, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test API Key"
        assert data["key"].startswith("ckd_")
        assert data["is_active"] is True
        assert data["scopes"] == ["repo:read", "claims:read"]

    async def test_create_api_key_unauthorized(self, async_client: AsyncClient):
        """Test API key creation without authorization."""
        key_data = {
            "name": "Test API Key",
            "description": "API key for testing",
            "scopes": ["repo:read"]
        }
        
        response = await async_client.post("/api/v1/auth/api-keys", json=key_data)
        
        assert response.status_code == 401

    async def test_list_api_keys(self, async_client: AsyncClient, test_user, user_token):
        """Test listing user's API keys."""
        headers = create_auth_headers(user_token)
        
        # First create an API key
        key_data = {
            "name": "Test API Key",
            "description": "API key for testing",
            "scopes": ["repo:read"]
        }
        await async_client.post("/api/v1/auth/api-keys", json=key_data, headers=headers)
        
        # List API keys
        response = await async_client.get("/api/v1/auth/api-keys", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["name"] == "Test API Key"
        assert "key" not in data[0]  # Should not expose actual key in list

    async def test_delete_api_key_success(self, async_client: AsyncClient, test_user, user_token):
        """Test successful API key deletion."""
        headers = create_auth_headers(user_token)
        
        # First create an API key
        key_data = {
            "name": "Test API Key to Delete",
            "description": "API key for testing deletion",
            "scopes": ["repo:read"]
        }
        create_response = await async_client.post("/api/v1/auth/api-keys", json=key_data, headers=headers)
        created_key = create_response.json()
        
        # Delete the API key
        response = await async_client.delete(f"/api/v1/auth/api-keys/{created_key['id']}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "deleted" in data["message"].lower()

    async def test_delete_api_key_not_found(self, async_client: AsyncClient, test_user, user_token):
        """Test deleting nonexistent API key."""
        headers = create_auth_headers(user_token)
        
        response = await async_client.delete("/api/v1/auth/api-keys/99999", headers=headers)
        
        assert response.status_code == 404

    async def test_api_key_authentication_success(self, async_client: AsyncClient, test_user, test_api_key):
        """Test successful API key authentication."""
        headers = create_api_key_headers(test_api_key)
        
        response = await async_client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email

    async def test_api_key_authentication_invalid(self, async_client: AsyncClient):
        """Test API key authentication with invalid key."""
        headers = create_api_key_headers("invalid_api_key")
        
        response = await async_client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 401


@pytest.mark.api
@pytest.mark.asyncio
class TestRoleBasedAccess:
    """Test role-based access control."""

    async def test_admin_only_endpoint_success(self, async_client: AsyncClient, test_admin_user, admin_token):
        """Test admin-only endpoint with admin user."""
        headers = create_auth_headers(admin_token)
        
        response = await async_client.get("/api/v1/admin/users", headers=headers)
        
        assert response.status_code == 200

    async def test_admin_only_endpoint_forbidden(self, async_client: AsyncClient, test_user, user_token):
        """Test admin-only endpoint with regular user."""
        headers = create_auth_headers(user_token)
        
        response = await async_client.get("/api/v1/admin/users", headers=headers)
        
        assert response.status_code == 403

    async def test_maintainer_endpoint_success(self, async_client: AsyncClient, test_maintainer_user, maintainer_token):
        """Test maintainer endpoint with maintainer user."""
        headers = create_auth_headers(maintainer_token)
        
        response = await async_client.get("/api/v1/repositories", headers=headers)
        
        assert response.status_code == 200

    async def test_maintainer_endpoint_with_admin(self, async_client: AsyncClient, test_admin_user, admin_token):
        """Test maintainer endpoint with admin user (should work)."""
        headers = create_auth_headers(admin_token)
        
        response = await async_client.get("/api/v1/repositories", headers=headers)
        
        assert response.status_code == 200

    async def test_user_endpoint_success(self, async_client: AsyncClient, test_user, user_token):
        """Test user endpoint with regular user."""
        headers = create_auth_headers(user_token)
        
        response = await async_client.get("/api/v1/claims", headers=headers)
        
        assert response.status_code == 200


@pytest.mark.api
@pytest.mark.asyncio
class TestPasswordManagement:
    """Test password management endpoints."""

    async def test_change_password_success(self, async_client: AsyncClient, test_user, user_token):
        """Test successful password change."""
        headers = create_auth_headers(user_token)
        
        password_data = {
            "current_password": "TestPassword123!",
            "new_password": "NewStrongPassword123!",
            "confirm_password": "NewStrongPassword123!"
        }
        
        response = await async_client.post("/api/v1/auth/change-password", json=password_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "password changed" in data["message"].lower()

    async def test_change_password_wrong_current(self, async_client: AsyncClient, test_user, user_token):
        """Test password change with wrong current password."""
        headers = create_auth_headers(user_token)
        
        password_data = {
            "current_password": "WrongPassword123!",
            "new_password": "NewStrongPassword123!",
            "confirm_password": "NewStrongPassword123!"
        }
        
        response = await async_client.post("/api/v1/auth/change-password", json=password_data, headers=headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "current password is incorrect" in data["detail"].lower()

    async def test_change_password_weak_new(self, async_client: AsyncClient, test_user, user_token):
        """Test password change with weak new password."""
        headers = create_auth_headers(user_token)
        
        password_data = {
            "current_password": "TestPassword123!",
            "new_password": "weak",
            "confirm_password": "weak"
        }
        
        response = await async_client.post("/api/v1/auth/change-password", json=password_data, headers=headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "password does not meet requirements" in data["detail"]["message"].lower()

    async def test_change_password_mismatch(self, async_client: AsyncClient, test_user, user_token):
        """Test password change with mismatched confirmation."""
        headers = create_auth_headers(user_token)
        
        password_data = {
            "current_password": "TestPassword123!",
            "new_password": "NewStrongPassword123!",
            "confirm_password": "DifferentPassword123!"
        }
        
        response = await async_client.post("/api/v1/auth/change-password", json=password_data, headers=headers)
        
        assert response.status_code == 400
        data = response.json()
        assert "passwords do not match" in data["detail"].lower()

    async def test_request_password_reset(self, async_client: AsyncClient, test_user):
        """Test password reset request."""
        reset_data = {
            "email": test_user.email
        }
        
        response = await async_client.post("/api/v1/auth/request-password-reset", json=reset_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "reset link sent" in data["message"].lower()

    async def test_request_password_reset_nonexistent(self, async_client: AsyncClient):
        """Test password reset request for nonexistent user."""
        reset_data = {
            "email": "nonexistent@example.com"
        }
        
        response = await async_client.post("/api/v1/auth/request-password-reset", json=reset_data)
        
        # Should return success even for nonexistent users (security)
        assert response.status_code == 200