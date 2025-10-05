"""
Status Command Module
"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

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