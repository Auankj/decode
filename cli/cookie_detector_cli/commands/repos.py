"""
Repository Command Module
Handles repository management with YOUR GitHub repositories only
"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Confirm
from .github_auth import authenticate_and_select_repos, get_your_github_username

console = Console()

def handle_repos(client, args):
    """Handle repository-related commands"""
    if args.repo_action == 'list':
        console.print("[bold blue]Listing Monitored Repositories...[/bold blue]")
        
        # Fetch real data from backend
        repos_data = client.make_api_request("/api/v1/repositories")
        
        if repos_data is None:
            # Show error if backend is not connected
            console.print("[red]✗ Could not connect to backend server[/red]")
            console.print("[yellow]Make sure the Cookie Licking Detector server is running[/yellow]")
            return
        
        repos = repos_data
        
        if not repos:
            console.print("[yellow]No repositories are currently being monitored[/yellow]")
            return
        
        table = Table(title="Monitored Repositories")
        table.add_column("ID", style="dim")
        table.add_column("Repository")
        table.add_column("Status")
        table.add_column("Grace Period")
        table.add_column("Nudges")
        
        for repo in repos:
            status = "[green]Active[/green]" if repo.get('is_monitored', False) else "[red]Inactive[/red]"
            table.add_row(
                str(repo.get('id', 'N/A')),
                repo.get('full_name', 'Unknown'),
                status,
                f"{repo.get('grace_period_days', 0)} days",
                str(repo.get('nudge_count', 0))
            )
        
        console.print(table)
        
    elif args.repo_action == 'register':
        console.print(f"[bold blue]Registering repository: {args.repo_full_name}[/bold blue]")
        
        # Parse the repository name (owner/repo format)
        if '/' not in args.repo_full_name:
            console.print(f"[red]✗ Invalid repository format. Use owner/repo format[/red]")
            return
            
        owner, name = args.repo_full_name.split('/', 1)
        
        # Call the actual API to register the repository
        data = {
            "owner": owner,
            "name": name
        }
        
        result = client.make_api_request("/api/v1/repositories", method="POST", data=data)
        
        if result:
            console.print(f"[green]✓ Repository {args.repo_full_name} registered successfully![/green]")
            console.print(f"  ID: {result.get('id', 'N/A')}")
            console.print(f"  URL: {result.get('url', 'N/A')}")
        else:
            console.print(f"[red]✗ Failed to register repository {args.repo_full_name}[/red]")
        
    elif args.repo_action == 'add' or args.repo_action is None:  # Default action
        console.print("[bold blue]Adding YOUR GitHub Repositories for Monitoring...[/bold blue]")
        
        # Authenticate and select YOUR repositories
        selected_repos = authenticate_and_select_repos()
        
        if not selected_repos:
            console.print("[yellow]⚠️  No repositories selected for monitoring[/yellow]")
            return
        
        # Register each selected repository
        registered_count = 0
        failed_repos = []
        
        for repo_full_name in selected_repos:
            console.print(f"[blue]Registering YOUR repository: {repo_full_name}...[/blue]")
            
            # Parse owner/name
            owner, name = repo_full_name.split('/', 1)
            data = {"owner": owner, "name": name}
            
            result = client.make_api_request("/api/v1/repositories", method="POST", data=data)
            
            if result:
                console.print(f"[green]✓ {repo_full_name} registered successfully![/green]")
                registered_count += 1
            else:
                console.print(f"[red]✗ Failed to register {repo_full_name}[/red]")
                failed_repos.append(repo_full_name)
        
        console.print(f"\n[green]✅ Successfully registered {registered_count}/{len(selected_repos)} of YOUR repositories[/green]")
        
        if failed_repos:
            console.print(f"[red]❌ Failed to register {len(failed_repos)} repositories:[/red]")
            for repo in failed_repos:
                console.print(f"  • {repo}")
        
        # Show how many total repos are now being monitored
        repos_data = client.make_api_request("/api/v1/repositories")
        if repos_data:
            total_monitored = len([r for r in repos_data if r.get('is_monitored', False)])
            console.print(f"[blue]📊 Total repositories now being monitored: {total_monitored}[/blue]")
        
    elif args.repo_action == 'unregister':
        console.print("[bold blue]Unregistering repository...[/bold blue]")
        
        # For now, we'll just demonstrate the concept
        console.print("[yellow]Unregister functionality would remove repository from monitoring[/yellow]")
        # This would call DELETE /api/v1/repositories/{id} in real implementation
    else:
        console.print("[red]❌ Invalid repository action. Use 'list', 'register', 'add', or 'unregister'.[/red]")
        console.print("  add      - Interactively select YOUR repos from your GitHub account")
        console.print("  list     - List monitored repositories") 
        console.print("  register - Register a specific repository (owner/repo)")
        console.print("  unregister - Stop monitoring a repository")