"""
Dashboard Command Module
"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from rich.spinner import Spinner
import time

console = Console()

def handle_dashboard(client):
    """Handle the dashboard command with real-time updates"""
    try:
        # Get dashboard data from backend
        dashboard_data = client.make_api_request("/api/v1/dashboard/stats")
        
        if dashboard_data is None:
            # Show error when backend is not connected
            console.print("[red]✗ Could not connect to backend server[/red]")
            console.print("[yellow]Make sure the Cookie Licking Detector server is running[/yellow]")
            # Show mock data as fallback
            show_mock_dashboard(client)
            return
        
        # Show actual dashboard with data from backend
        show_real_dashboard(client, dashboard_data)
        
    except KeyboardInterrupt:
        console.print("\n[blue]Dashboard stopped by user[/blue]")

def show_mock_dashboard(client):
    """Show dashboard with mock data"""
    console.print(Panel("[bold blue]Cookie Licking Detector Dashboard (Mock Data)[/bold blue]"))
    
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

def show_real_dashboard(client, dashboard_data):
    """Show dashboard with real data from backend"""
    console.print(Panel("[bold blue]Cookie Licking Detector Dashboard (Live)[/bold blue]"))
    
    # Extract and display the actual dashboard data based on the real structure
    overview = dashboard_data.get('overview', {})
    metrics = dashboard_data.get('metrics', {})
    
    console.print(f"[bold]Total Claims:[/bold] {overview.get('total_claims', 0)}")
    console.print(f"[bold]Active Claims:[/bold] {overview.get('active_claims', 0)}")
    console.print(f"[bold]Released Claims:[/bold] {overview.get('released_claims', 0)}")
    console.print(f"[bold]Completed Claims:[/bold] {overview.get('completed_claims', 0)}")
    console.print(f"[bold]Recent Claims (7d):[/bold] {metrics.get('recent_claims_7d', 0)}")
    
    # Show additional metrics
    console.print(f"[bold]Auto-Release Rate:[/bold] {metrics.get('auto_release_rate', 0.0)}%")
    if metrics.get('avg_time_to_release_days', 0) > 0:
        console.print(f"[bold]Avg. Time to Release:[/bold] {metrics.get('avg_time_to_release_days', 0)} days")
    
    # Show confidence distribution
    confidence_dist = dashboard_data.get('confidence_distribution', {})
    if confidence_dist:
        console.print("\n[bold]Confidence Distribution:[/bold]")
        for conf, count in confidence_dist.items():
            console.print(f"  {conf}% confidence: {count} claims")
    
    console.print(f"[bold]Generated At:[/bold] {dashboard_data.get('generated_at', 'Unknown')}")