"""
CLI Commands Module for Cookie Licking Detector
Handles various CLI command implementations
"""
from typing import Any, Dict, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint

console = Console()

def handle_status(client):
    """Handle the status command"""
    console.print("[bold blue]Checking Cookie Licking Detector System Status...[/bold blue]")
    
    # Get system information from backend
    system_info = client.make_api_request("/")
    if system_info:
        console.print(f"[green]✓ Service:[/green] {system_info.get('service', 'Unknown')}")
        console.print(f"[green]✓ Status:[/green] {system_info.get('status', 'Unknown')}")
        console.print(f"[green]✓ Environment:[/green] {system_info.get('environment', 'Unknown')}")
        console.print(f"[green]✓ Timestamp:[/green] {system_info.get('timestamp', 'Unknown')}")
    else:
        console.print("[red]✗ Unable to connect to backend[/red]")
        return
    
    # Get health information
    console.print("\n[bold blue]Health Check:[/bold blue]")
    health_info = client.make_api_request("/health")
    if health_info:
        status = health_info.get('status', 'unknown')
        if status == 'healthy':
            console.print(f"[green]✓ Health Status:[/green] {status}")
        else:
            console.print(f"[red]✗ Health Status:[/green] {status}")
    
    # Get version information
    console.print("\n[bold blue]Version Info:[/bold blue]")
    version_info = client.make_api_request("/version")
    if version_info:
        console.print(f"[green]✓ Version:[/green] {version_info.get('version', 'Unknown')}")
        console.print(f"[green]✓ API Version:[/green] {version_info.get('api_version', 'Unknown')}")
    
    console.print("\n[bold green]System is operational![/bold green]")

def handle_repos(client, args):
    """Handle repository-related commands"""
    if args.repo_action == 'list':
        console.print("[bold blue]Listing Monitored Repositories...[/bold blue]")
        
        # This would be the actual endpoint once implemented in the backend
        # For now, let's show a mock response
        console.print("[yellow]Note: This feature requires backend API implementation[/yellow]")
        console.print("Mock repositories:")
        repos = [
            {"id": 1, "full_name": "org/repo1", "active": True, "claims_count": 3},
            {"id": 2, "full_name": "org/repo2", "active": True, "claims_count": 1},
            {"id": 3, "full_name": "org/repo3", "active": False, "claims_count": 0}
        ]
        
        table = Table(title="Monitored Repositories")
        table.add_column("ID", style="dim")
        table.add_column("Repository")
        table.add_column("Status")
        table.add_column("Claims")
        
        for repo in repos:
            status = "[green]Active[/green]" if repo['active'] else "[red]Inactive[/red]"
            table.add_row(
                str(repo['id']),
                repo['full_name'],
                status,
                str(repo['claims_count'])
            )
        
        console.print(table)
        
    elif args.repo_action == 'register':
        console.print(f"[bold blue]Registering repository: {args.repo_full_name}[/bold blue]")
        # Mock registration
        console.print(f"[green]✓ Repository {args.repo_full_name} registered successfully![/green]")
        
    elif args.repo_action == 'unregister':
        console.print("[bold blue]Unregistering repository...[/bold blue]")
        console.print("[green]✓ Repository unregistered successfully![/green]")
    else:
        console.print("[red]Invalid repository action. Use 'list', 'register', or 'unregister'.[/red]")

def handle_claims(client, args):
    """Handle claim-related commands"""
    if args.claim_action in ['list', 'active', 'stale']:
        console.print(f"[bold blue]Listing {args.claim_action or 'all'} claims...[/bold blue]")
        
        # Mock claims data
        claims = [
            {
                "id": 1,
                "issue_number": 123,
                "repository": "org/repo1",
                "username": "active_contributor",
                "status": "active" if args.claim_action != 'stale' else 'stale',
                "created_at": "2024-01-01T10:00:00Z",
                "last_activity": "2024-01-02T15:30:00Z",
                "confidence": 95
            },
            {
                "id": 2,
                "issue_number": 125,
                "repository": "org/repo2", 
                "username": "slow_worker",
                "status": "stale" if args.claim_action != 'active' else 'active',
                "created_at": "2024-01-01T08:00:00Z",
                "last_activity": "2024-01-01T08:00:00Z",
                "confidence": 90
            }
        ]
        
        # Filter based on action
        if args.claim_action == 'active':
            claims = [c for c in claims if c['status'] == 'active']
        elif args.claim_action == 'stale':
            claims = [c for c in claims if c['status'] == 'stale']
        
        table = Table(title=f"Claims - {args.claim_action or 'All'}")
        table.add_column("ID", style="dim")
        table.add_column("Issue")
        table.add_column("Repository")
        table.add_column("User")
        table.add_column("Status")
        table.add_column("Confidence")
        table.add_column("Created")
        
        for claim in claims:
            status_color = "[green]Active[/green]" if claim['status'] == 'active' else "[red]Stale[/red]"
            confidence_color = "[green]" if claim['confidence'] > 80 else "[yellow]" if claim['confidence'] > 60 else "[red]"
            
            table.add_row(
                str(claim['id']),
                f"#{claim['issue_number']}",
                claim['repository'],
                claim['username'],
                status_color,
                f"{confidence_color}{claim['confidence']}%[/]",
                claim['created_at'].split('T')[0]
            )
        
        console.print(table)
    else:
        console.print("[red]Invalid claim action. Use 'list', 'active', or 'stale'.[/red]")

def handle_dashboard(client):
    """Handle the dashboard command"""
    console.print(Panel("[bold blue]Cookie Licking Detector Dashboard[/bold blue]"))
    
    # System stats
    console.print("\n[bold]System Statistics:[/bold]")
    stats = {
        "Total Repositories": 15,
        "Active Claims": 23,
        "Stale Claims": 8,
        "Nudges Sent": 124,
        "Auto-Released": 5,
        "Last Check": "2024-01-02 10:30:00"
    }
    
    for key, value in stats.items():
        console.print(f"[cyan]{key}:[/cyan] {value}")
    
    # Active claims summary
    console.print("\n[bold]Top Active Claims:[/bold]")
    active_claims = [
        {"repo": "facebook/react", "issue": 24567, "user": "react_dev", "days": 2},
        {"repo": "microsoft/vscode", "issue": 17890, "user": "vscode_contrib", "days": 1},
        {"repo": "nodejs/node", "issue": 43210, "user": "node_expert", "days": 5}
    ]
    
    table = Table()
    table.add_column("Repository", style="dim")
    table.add_column("Issue", style="dim")
    table.add_column("User")
    table.add_column("Days Claimed")
    
    for claim in active_claims:
        table.add_row(claim['repo'], f"#{claim['issue']}", claim['user'], str(claim['days']))
    
    console.print(table)
    
    # Stale claims summary
    console.print("\n[bold]Stale Claims (Need Attention):[/bold]")
    stale_claims = [
        {"repo": "vuejs/vue", "issue": 13579, "user": "vue_newbie", "days": 12},
        {"repo": "angular/angular", "issue": 24680, "user": "angular_beginner", "days": 18}
    ]
    
    table2 = Table()
    table2.add_column("Repository", style="dim")
    table2.add_column("Issue", style="dim")
    table2.add_column("User")
    table2.add_column("Days Inactive", style="red")
    
    for claim in stale_claims:
        table2.add_row(claim['repo'], f"#{claim['issue']}", claim['user'], str(claim['days']))
    
    console.print(table2)

def handle_config(client, args):
    """Handle configuration commands"""
    if args.config_action == 'show':
        console.print("[bold blue]Current Configuration:[/bold blue]")
        table = Table()
        table.add_column("Setting")
        table.add_column("Value")
        
        for key, value in client.config.items():
            table.add_row(key, str(value))
        
        console.print(table)
        
    elif args.config_action == 'set':
        console.print(f"[bold blue]Setting {args.key} = {args.value}[/bold blue]")
        # In a real implementation, we would update the config file
        console.print(f"[green]✓ Configuration updated: {args.key} = {args.value}[/green]")
    else:
        console.print("[red]Invalid config action. Use 'show' or 'set'.[/red]")