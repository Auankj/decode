"""
Configuration Command Module
"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from pathlib import Path
import toml

console = Console()

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
        
        # Update the configuration
        client.config[args.key] = args.value
        
        # Save the updated configuration to file
        config_path = Path.home() / '.cookie_detector' / 'config.toml'
        with open(config_path, 'w') as f:
            toml.dump(client.config, f)
        
        console.print(f"[green]✓ Configuration updated: {args.key} = {args.value}[/green]")
    else:
        console.print("[red]Invalid config action. Use 'show' or 'set'.[/red]")