"""
GitHub Authentication Module for CLI
Handles GitHub OAuth flow and repository selection for YOUR repositories only
"""
import requests
import webbrowser
import urllib.parse
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import json
import time
import os
from pathlib import Path
from typing import Dict, List, Optional

console = Console()

class GitHubAuth:
    """Handles GitHub OAuth authentication for CLI and fetches YOUR repositories"""
    
    def __init__(self):
        # Use the existing token from environment or config file
        self.access_token = self.get_access_token()
    
    def get_access_token(self) -> Optional[str]:
        """Get GitHub access token - prioritizes environment variable then config file"""
        # First check environment variable
        env_token = os.getenv('GITHUB_TOKEN')
        if env_token:
            return env_token
            
        # Then check config file
        return self.get_saved_token()
    
    def save_token(self, token: str):
        """Save GitHub access token to config file"""
        config_path = Path.home() / '.cookie_detector' / 'github_token.json'
        config_path.parent.mkdir(exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump({'access_token': token}, f)
    
    def get_saved_token(self) -> Optional[str]:
        """Get saved GitHub access token from config file"""
        config_path = Path.home() / '.cookie_detector' / 'github_token.json'
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    return data.get('access_token')
            except Exception as e:
                console.print(f"[red]Error reading saved token: {e}[/red]")
        return None
    
    def get_your_repos(self) -> List[Dict]:
        """Get YOUR repositories from GitHub API"""
        token = self.get_access_token()
        if not token:
            console.print("[red]Error: No GitHub access token available[/red]")
            console.print("[yellow]Please set GITHUB_TOKEN environment variable or run 'cookie-detector github setup'[/yellow]")
            return []
        
        try:
            headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Get user's repositories with pagination
            repos = []
            page = 1
            
            while True:
                response = requests.get(
                    f'https://api.github.com/user/repos',
                    headers=headers,
                    params={'page': page, 'per_page': 100, 'type': 'all', 'sort': 'updated', 'direction': 'desc'}
                )
                
                if response.status_code != 200:
                    console.print(f"[red]Error fetching your repositories: {response.status_code}[/red]")
                    console.print(f"[yellow]Response: {response.text}[/yellow]")
                    break
                    
                page_repos = response.json()
                if not page_repos:  # No more repositories
                    break
                    
                repos.extend(page_repos)
                page += 1
                
                # Safety break to prevent infinite loops
                if page > 10:  # Max 1000 repos
                    break
            
            return repos
            
        except Exception as e:
            console.print(f"[red]Error fetching your repositories: {e}[/red]")
            return []

def authenticate_and_select_repos() -> List[str]:
    """Authenticate with GitHub and select YOUR repositories for monitoring"""
    auth = GitHubAuth()
    
    # Check if we have a token
    token = auth.get_access_token()
    if not token:
        console.print("[red]❌ No GitHub access token available[/red]")
        console.print("[yellow]💡 Please run 'cookie-detector github setup' to configure your GitHub token[/yellow]")
        return []
    
    console.print("[green]✅ Using existing GitHub token to fetch YOUR repositories[/green]")
    
    # Get user's repositories
    repos = auth.get_your_repos()
    
    if not repos:
        console.print("[yellow]⚠️  No repositories found or access denied[/yellow]")
        return []
    
    console.print(f"[green]✅ Found {len(repos)} of YOUR repositories[/green]")
    
    # Filter to show only repositories the user can manage (has admin/push permissions)
    manageable_repos = []
    for repo in repos:
        permissions = repo.get('permissions', {})
        # Check if user has admin or push permissions
        if permissions.get('admin', False) or permissions.get('push', False):
            manageable_repos.append(repo)
    
    if not manageable_repos:
        console.print("[yellow]⚠️  No repositories with admin/push permissions found[/yellow]")
        return []
    
    console.print(f"[green]✅ Found {len(manageable_repos)} repositories you can manage[/green]")
    
    # Create a table of repositories for selection
    table = Table(title="Select YOUR Repositories to Monitor")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Repository")
    table.add_column("Private", style="dim")
    table.add_column("Language", style="dim")
    table.add_column("Stars", style="dim", justify="right")
    table.add_column("Forks", style="dim", justify="right")
    
    for i, repo in enumerate(manageable_repos, 1):
        private = "[red]PRIVATE[/red]" if repo.get('private', False) else "[green]PUBLIC[/green]"
        language = repo.get('language', 'N/A') or 'N/A'
        stars = str(repo.get('stargazers_count', 0))
        forks = str(repo.get('forks_count', 0))
        table.add_row(str(i), repo['full_name'], private, language, stars, forks)
    
    console.print(table)
    
    # Ask user to select repositories
    console.print("\n[blue]Enter comma-separated numbers of repositories to monitor (e.g., 1,3,5) or 'all':[/blue]")
    selection = Prompt.ask("Selection")
    
    selected_repos = []
    
    if selection.lower() == 'all':
        selected_repos = [repo['full_name'] for repo in manageable_repos]
    else:
        try:
            indices = [int(x.strip()) - 1 for x in selection.split(',')]
            selected_repos = [
                manageable_repos[i]['full_name'] 
                for i in indices 
                if 0 <= i < len(manageable_repos)
            ]
        except ValueError:
            console.print("[red]❌ Invalid selection format[/red]")
            return []
    
    if not selected_repos:
        console.print("[yellow]⚠️  No repositories selected[/yellow]")
        return []
    
    console.print(f"[green]✅ Selected {len(selected_repos)} of YOUR repositories:[/green]")
    for repo in selected_repos:
        console.print(f"  • {repo}")
    
    if Confirm.ask(f"\n[yellow]Monitor these {len(selected_repos)} repositories?[/yellow]"):
        return selected_repos
    else:
        console.print("[yellow]⚠️  Repository selection cancelled[/yellow]")
        return []

def get_your_github_username() -> Optional[str]:
    """Get your GitHub username from the API"""
    auth = GitHubAuth()
    token = auth.get_access_token()
    
    if not token:
        return None
    
    try:
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        response = requests.get('https://api.github.com/user', headers=headers)
        
        if response.status_code == 200:
            user_data = response.json()
            return user_data.get('login')
        else:
            console.print(f"[red]Error fetching user info: {response.status_code}[/red]")
            return None
            
    except Exception as e:
        console.print(f"[red]Error fetching user info: {e}[/red]")
        return None