"""
Claims Command Module
"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console()

def handle_claims(client, args):
    """Handle claim-related commands"""
    if args.claim_action in ['list', 'active', 'stale', None]:
        action = args.claim_action or 'all'
        console.print(f"[bold blue]Listing {action} claims...[/bold blue]")
        
        # Fetch actual data from backend using correct API path
        claims_data = client.make_api_request("/api/v1/claims")
        
        if claims_data is None:
            # Show proper error if backend is not connected
            console.print("[red]✗ Could not connect to backend server[/red]")
            console.print("[yellow]Make sure the Cookie Licking Detector server is running[/yellow]")
            return
        
        # The API returns a dictionary with a 'claims' key
        claims = claims_data.get('claims', []) if isinstance(claims_data, dict) else claims_data
        
        if not claims:
            console.print("[yellow]No claims found[/yellow]")
            return
        
        # Filter based on action if needed
        if args.claim_action == 'active':
            claims = [c for c in claims if c.get('status', '').upper() == 'ACTIVE']
        elif args.claim_action == 'stale':
            claims = [c for c in claims if c.get('status', '').upper() == 'STALE' or c.get('status', '').upper() == 'AUTO_RELEASED']
        
        if not claims:
            console.print(f"[yellow]No {action} claims found[/yellow]")
            return
        
        table = Table(title=f"Claims - {action.title()}")
        table.add_column("ID", style="dim")
        table.add_column("Issue")
        table.add_column("Repository")
        table.add_column("User")
        table.add_column("Status")
        table.add_column("Confidence")
        table.add_column("Created")
        
        for claim in claims:
            status = claim.get('status', '').upper()
            status_color = "[green]ACTIVE[/green]" if status == 'ACTIVE' else "[red]STALE[/red]" if status == 'STALE' else f"[yellow]{status}[/yellow]"
            confidence = claim.get('confidence_score', claim.get('confidence', 0))
            confidence_color = "[green]" if confidence > 80 else "[yellow]" if confidence > 60 else "[red]"
            
            table.add_row(
                str(claim.get('id', 'N/A')),
                f"#{claim.get('issue_number', claim.get('issue', {}).get('github_issue_number', 'N/A'))}",
                claim.get('repository_name', 'Unknown'),
                claim.get('github_username', claim.get('username', 'Unknown')),
                status_color,
                f"{confidence_color}{confidence}%[/]",
                claim.get('claim_timestamp', 'Unknown').split('T')[0]
            )
        
        console.print(table)
    else:
        console.print("[red]Invalid claim action. Use 'list', 'active', or 'stale'.[/red]")