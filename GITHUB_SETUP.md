# GitHub Integration Setup Guide

## 1. Create a GitHub Personal Access Token

1. Go to GitHub Settings: https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Select these scopes:
   - `repo` (Full control of private repositories)
   - `issues` (Read/write access to issues) 
   - `pull_requests` (Read/write access to pull requests)
   - `admin:repo_hook` (Read/write access to repository hooks)

4. Copy the generated token (starts with `ghp_`)
5. Add it to your `.env` file:
   ```bash
   GITHUB_TOKEN=ghp_your_token_here
   ```

## 2. Set up Webhook (Optional - for production)

1. Go to your repository settings
2. Click "Webhooks" → "Add webhook"  
3. Set payload URL to: `https://your-domain.com/webhooks/github`
4. Content type: `application/json`
5. Select events: `Issues`, `Issue comments`, `Pull requests`, `Pushes`
6. Generate a webhook secret and add to `.env`:
   ```bash
   GITHUB_WEBHOOK_SECRET=your_webhook_secret
   ```

## 3. Test GitHub Integration

Run the following command to test:

```bash
python3 -c "
from app.services.github_service import GitHubAPIService
service = GitHubAPIService()
print('GitHub service initialized:', service.authenticated)
"
```

## For Development

You can test without a token - the service will work in unauthenticated mode with rate limits.