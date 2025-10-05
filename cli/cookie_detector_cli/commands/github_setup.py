"""
GitHub Setup Command Module
Handles GitHub API token configuration and validation
"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
import requests
import json
import os
from pathlib import Path
from typing import Optional

console = Console()

class GitHubTokenManager:
    """Manages GitHub token storage and validation"""
    
    def __init__(self):
        self.config_path = Path.home() / '.cookie_detector' / 'github_token.json'
        self.config_path.parent.mkdir(exist_ok=True)
    
    def save_token(self, token: str) -> bool:
        """Save GitHub token to config file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump({'access_token': token}, f)
            return True
        except Exception as e:
            console.print(f"[red]❌ Error saving token: {e}[/red]")
            return False
    
    def get_token(self) -> Optional[str]:
        """Get saved GitHub token from config file"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    return data.get('access_token')
            except Exception as e:
                console.print(f"[red]❌ Error reading token: {e}[/red]")
        return None
    
    def delete_token(self) -> bool:
        """Delete saved GitHub token"""
        try:
            if self.config_path.exists():
                self.config_path.unlink()
            return True
        except Exception as e:
            console.print(f"[red]❌ Error deleting token: {e}[/red]")
            return False
    
    def validate_token(self, token: str) -> bool:
        """Validate GitHub token by making a test API call"""
        try:
            headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.get('https://api.github.com/user', headers=headers, timeout=10)
            
            if response.status_code == 200:
                user_data = response.json()
                console.print(f"[green]✅ Token is valid for user: {user_data.get('login', 'Unknown')}[/green]")
                return True
            elif response.status_code == 401:
                console.print("[red]❌ Invalid token: Unauthorized (401)[/red]")
                return False
            else:
                console.print(f"[red]❌ Token validation failed: {response.status_code}[/red]")
                return False
                
        except requests.exceptions.Timeout:
            console.print("[red]❌ Token validation timed out[/red]")
            return False
        except Exception as e:
            console.print(f"[red]❌ Error validating token: {e}[/red]")
            return False

def handle_github_setup() -> bool:
    """Handle GitHub setup wizard"""
    console.print(Panel("[bold blue]GitHub API Token Setup[/bold blue]\n\n"
                       "To use the Cookie Licking Detector with your GitHub repositories,\n"
                       "you need to provide a GitHub Personal Access Token.\n\n"
                       "[yellow]Instructions:[/yellow]\n"
                       "1. Go to https://github.com/settings/tokens\n"
                       "2. Click 'Generate new token' -> 'Fine-grained tokens'\n"
                       "3. Give it a name like 'Cookie Licking Detector'\n"
                       "4. Grant repository permissions:\n"
                       "   - Contents: Read\n"
                       "   - Issues: Read and write\n"
                       "   - Pull requests: Read\n"
                       "5. Copy the generated token\n\n"
                       "[yellow]Note:[/yellow] Your token will be stored securely in ~/.cookie_detector/github_token.json"))
    
    # Check if token already exists
    token_manager = GitHubTokenManager()
    existing_token = token_manager.get_token()
    
    if existing_token:
        console.print("[yellow]⚠️  Existing token found[/yellow]")
        if not Confirm.ask("Do you want to replace it?"):
            console.print("[blue]ℹ️  Keeping existing token[/blue]")
            return True
    
    # Get token from user
    while True:
        token = Prompt.ask("Enter your GitHub Personal Access Token", password=True)
        
        if not token:
            console.print("[red]❌ Token cannot be empty[/red]")
            continue
            
        if len(token) < 10:
            console.print("[red]❌ Token seems too short. Please check and try again.[/red]")
            continue
        
        break
    
    # Validate token
    console.print("[blue]🔄 Validating token...[/blue]")
    if not token_manager.validate_token(token):
        console.print("[red]❌ Token validation failed. Please check the token and try again.[/red]")
        return False
    
    # Save token
    if token_manager.save_token(token):
        console.print("[green]✅ GitHub token saved successfully![/green]")
        console.print("[green]🎉 You can now use 'cookie-detector repos add' to select your repositories![/green]")
        return True
    else:
        console.print("[red]❌ Failed to save token[/red]")
        return False

def handle_github_status() -> bool:
    """Handle GitHub status check"""
    console.print("[bold blue]GitHub Integration Status[/bold blue]")
    
    token_manager = GitHubTokenManager()
    token = token_manager.get_token()
    
    if not token:
        console.print("[red]❌ No GitHub token configured[/red]")
        console.print("[yellow]💡 Run 'cookie-detector github setup' to configure your token[/yellow]")
        return False
    
    console.print("[green]✅ GitHub token found in configuration[/green]")
    
    # Validate token
    console.print("[blue]🔄 Checking token validity...[/blue]")
    if token_manager.validate_token(token):
        console.print("[green]✅ Token is valid and working[/green]")
        
        # Get user info
        try:
            headers = {
                'Authorization': f'token {token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.get('https://api.github.com/user', headers=headers, timeout=10)
            
            if response.status_code == 200:
                user_data = response.json()
                console.print(f"[green]👤 Authenticated as: {user_data.get('login', 'Unknown')}[/green]")
                
                # Show repository count
                repos_response = requests.get(
                    'https://api.github.com/user/repos', 
                    headers=headers, 
                    params={'per_page': 1},
                    timeout=10
                )
                
                if repos_response.status_code == 200:
                    repo_count = repos_response.headers.get('Link')
                    if repo_count:
                        # Parse Link header to get total count
                        # This is a simplified approach
                        console.print("[green]📊 Repository access confirmed[/green]")
                    else:
                        console.print("[green]📊 Repository access confirmed[/green]")
                        
        except Exception as e:
            console.print(f"[yellow]⚠️  Warning: Could not fetch user details: {e}[/yellow]")
    else:
        console.print("[red]❌ Token is invalid or expired[/red]")
        console.print("[yellow]💡 Run 'cookie-detector github setup' to configure a new token[/yellow]")
        return False
    
    return True

def handle_github(client, args):
    """Handle GitHub-related commands"""
    if args.github_action == 'setup':
        handle_github_setup()
    elif args.github_action == 'status':
        handle_github_status()
    else:
        console.print("[red]❌ Invalid GitHub action. Use 'setup' or 'status'.[/red]")
        console.print("  setup   - Configure GitHub API token")
        console.print("  status  - Check GitHub integration status")