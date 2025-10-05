"""
Cookie Licking Detector CLI - Main Entry Point
A comprehensive command-line interface for the Cookie Licking Detector system
"""
import os
import sys
import argparse
from typing import Optional
from pathlib import Path

# Add the parent project to path to access backend modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint
from rich.progress import Progress, SpinnerColumn, TextColumn
import toml  # For config file management

console = Console()

class CLIClient:
    """Main CLI client for Cookie Licking Detector"""
    
    def __init__(self):
        self.config = self.load_config()
        self.api_base_url = self.config.get('api_url', 'http://localhost:8000')
        self.console = Console()
    
    def load_config(self) -> dict:
        """Load configuration from config file or create default"""
        config_path = Path.home() / '.cookie_detector' / 'config.toml'
        
        # Create default config if not exists
        if not config_path.exists():
            config_path.parent.mkdir(exist_ok=True)
            default_config = {
                'api_url': 'http://localhost:8000',
                'default_grace_period': 7,
                'default_nudge_count': 2
            }
            with open(config_path, 'w') as f:
                toml.dump(default_config, f)
            return default_config
        
        # Load existing config
        with open(config_path, 'r') as f:
            return toml.load(f)
    
    def make_api_request(self, endpoint: str, method: str = 'GET', data: Optional[dict] = None) -> dict:
        """Make an API request to the backend"""
        # Construct the full URL - the endpoint should include the full path
        url = f"{self.api_base_url}{endpoint}"
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Cookie-Detector-CLI/1.0'
        }
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            # Return None for client errors (4xx) and server errors (5xx)
            if 400 <= response.status_code < 600:
                console.print(f"[red]API Error ({response.status_code}): {response.text}[/red]")
                return None
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            console.print("[red]Error: Cannot connect to backend server[/red]")
            console.print(f"[yellow]Make sure the server is running at {self.api_base_url}[/yellow]")
            return None
        except requests.exceptions.HTTPError as e:
            console.print(f"[red]HTTP Error: {e}[/red]")
            return None
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return None

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        prog='cookie-detector',
        description='Cookie Licking Detector - CLI for managing GitHub issue claims',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cookie-detector status                    # Check system status
  cookie-detector repos list               # List monitored repositories
  cookie-detector claims list              # List all claims
  cookie-detector dashboard                # Show real-time dashboard
  cookie-detector config set api_url http://localhost:8000  # Set API URL
        """
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version='1.0.0'
    )
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    subparsers.add_parser('status', help='Check system status')
    
    # Repository commands
    repo_parser = subparsers.add_parser('repos', help='Repository management')
    repo_subparsers = repo_parser.add_subparsers(dest='repo_action')
    repo_subparsers.add_parser('list', help='List monitored repositories')
    repo_subparsers.add_parser('add', help='Add repositories from your GitHub account')
    register_parser = repo_subparsers.add_parser('register', help='Register a specific repository')
    register_parser.add_argument('repo_full_name', help='Repository full name (owner/repo)')
    repo_subparsers.add_parser('unregister', help='Unregister a repository')
    
    # Claim commands
    claim_parser = subparsers.add_parser('claims', help='Claim management')
    claim_subparsers = claim_parser.add_subparsers(dest='claim_action')
    claim_subparsers.add_parser('list', help='List all claims')
    claim_subparsers.add_parser('stale', help='List stale claims')
    claim_subparsers.add_parser('active', help='List active claims')
    
    # Dashboard command
    subparsers.add_parser('dashboard', help='Show real-time dashboard')
    
    # Configuration command
    config_parser = subparsers.add_parser('config', help='Configuration management')
    config_subparsers = config_parser.add_subparsers(dest='config_action')
    config_subparsers.add_parser('show', help='Show current configuration')
    set_parser = config_subparsers.add_parser('set', help='Set configuration value')
    set_parser.add_argument('key', help='Configuration key')
    set_parser.add_argument('value', help='Configuration value')
    
    # GitHub configuration command
    github_parser = subparsers.add_parser('github', help='GitHub integration configuration')
    github_subparsers = github_parser.add_subparsers(dest='github_action')
    github_subparsers.add_parser('setup', help='Configure GitHub API token')
    github_subparsers.add_parser('status', help='Check GitHub integration status')
    
    # Task management command
    task_parser = subparsers.add_parser('tasks', help='Background task management')
    task_subparsers = task_parser.add_subparsers(dest='task_action')
    task_subparsers.add_parser('status', help='Show task status')
    
    # Worker management command
    subparsers.add_parser('workers', help='Celery worker status')
    
    # Notification management command
    notification_parser = subparsers.add_parser('notifications', help='Notification management')
    notification_subparsers = notification_parser.add_subparsers(dest='notification_action')
    notification_subparsers.add_parser('history', help='Show notification history')
    
    # Alert management command
    subparsers.add_parser('alerts', help='System alerts')
    
    # Analytics and reporting commands
    analytics_parser = subparsers.add_parser('analytics', help='Analytics and reporting')
    analytics_subparsers = analytics_parser.add_subparsers(dest='analytics_action')
    analytics_subparsers.add_parser('summary', help='Show analytics summary')
    
    # Report generation command
    report_parser = subparsers.add_parser('report', help='Generate reports')
    report_parser.add_argument('--format', choices=['csv', 'json', 'excel'], default='json',
                              help='Output format for export (default: json)')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Initialize client
    client = CLIClient()
    
    # Dispatch to appropriate handler
    if args.command == 'status':
        from .commands.status import handle_status
        handle_status(client)
    elif args.command == 'repos':
        from .commands.repos import handle_repos
        handle_repos(client, args)
    elif args.command == 'claims':
        from .commands.claims import handle_claims
        handle_claims(client, args)
    elif args.command == 'dashboard':
        from .commands.dashboard import handle_dashboard
        handle_dashboard(client)
    elif args.command == 'config':
        from .commands.config import handle_config
        handle_config(client, args)
    elif args.command == 'github':
        from .commands.github_setup import handle_github
        handle_github(client, args)
    elif args.command == 'tasks':
        from .commands.tasks import handle_tasks
        handle_tasks(client, args)
    elif args.command == 'workers':
        from .commands.tasks import handle_workers
        handle_workers(client, args)
    elif args.command == 'notifications':
        from .commands.notifications import handle_notifications
        handle_notifications(client, args)
    elif args.command == 'alerts':
        from .commands.notifications import handle_alerts
        handle_alerts(client, args)
    elif args.command == 'analytics':
        from .commands.analytics import handle_analytics
        handle_analytics(client, args)
    elif args.command == 'report':
        from .commands.analytics import handle_report
        handle_report(client, args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()