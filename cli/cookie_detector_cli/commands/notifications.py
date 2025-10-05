"""
Advanced Command Module - Notifications
"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import json

console = Console()

def handle_notifications(client, args):
    """Handle notification management"""
    if args.notification_action == 'history':
        console.print("[bold blue]Fetching Notification History...[/bold blue]")
        
        # Try to fetch real notification history from backend
        # Look for potential endpoints that might exist
        notifications_data = client.make_api_request("/api/v1/activity_log")  # Common pattern
        
        if notifications_data is not None:
            # If we get real data, display it
            console.print(f"[green]Found {len(notifications_data)} activity records[/green]")
            
            table = Table(title="Notification History")
            table.add_column("ID", style="dim")
            table.add_column("Type")
            table.add_column("User")
            table.add_column("Repository")
            table.add_column("Issue")
            table.add_column("Status")
            table.add_column("Timestamp")
            
            for activity in notifications_data:
                activity_type = activity.get('activity_type', 'unknown')
                status_color = "[green]completed[/green]" if 'sent' in activity_type.lower() or 'completed' in activity_type.lower() else "[blue]logged[/blue]"
                
                table.add_row(
                    str(activity.get('id', 'N/A')),
                    activity_type,
                    activity.get('actor', {}).get('username', 'Unknown'),
                    activity.get('repository', {}).get('full_name', 'Unknown'),
                    f"#{activity.get('issue_number', 'N/A')}",
                    status_color,
                    activity.get('timestamp', 'Unknown')[0:10]
                )
            
            console.print(table)
        else:
            # Fallback to mock data
            console.print("[yellow]Note: Notification API not available, showing mock data[/yellow]")
            notifications = [
                {
                    "id": 1,
                    "type": "nudge",
                    "recipient": "contributor1",
                    "repository": "org/repo1",
                    "issue": 123,
                    "sent_at": "2024-01-01T10:00:00Z",
                    "status": "delivered"
                },
                {
                    "id": 2,
                    "type": "auto_release",
                    "recipient": "inactive_user",
                    "repository": "org/repo2", 
                    "issue": 125,
                    "sent_at": "2024-01-01T11:30:00Z",
                    "status": "delivered"
                },
                {
                    "id": 3,
                    "type": "github_comment",
                    "recipient": "maintainer",
                    "repository": "org/repo1",
                    "issue": 123,
                    "sent_at": "2024-01-01T12:00:00Z",
                    "status": "pending"
                }
            ]
            
            table = Table(title="Notification History")
            table.add_column("ID", style="dim")
            table.add_column("Type")
            table.add_column("Recipient")
            table.add_column("Repository")
            table.add_column("Issue")
            table.add_column("Status")
            table.add_column("Sent At")
            
            for note in notifications:
                status_color = "[green]delivered[/green]" if note['status'] == 'delivered' else "[yellow]pending[/yellow]"
                table.add_row(
                    str(note['id']),
                    note['type'],
                    note['recipient'],
                    note['repository'],
                    f"#{note['issue']}",
                    status_color,
                    note['sent_at'].split('T')[0]
                )
            
            console.print(table)
    else:
        console.print("[red]Invalid notification action. Use 'history'.[/red]")

def handle_alerts(client, args):
    """Handle system alerts"""
    console.print("[bold blue]Fetching System Alerts...[/bold blue]")
    
    # Try to fetch real alert data from backend
    # This might be part of dashboard stats or a separate endpoint
    dashboard_data = client.make_api_request("/api/v1/dashboard/stats")
    
    if dashboard_data is not None:
        # Extract alert-like information from dashboard
        alerts = []
        
        # Look for stale claims that could be considered alerts
        stale_count = dashboard_data.get('stale_claims', 0)
        if stale_count > 0:
            alerts.append({
                "id": 1,
                "type": "stale_claim",
                "severity": "medium",
                "message": f"{stale_count} stale claims need attention",
                "created_at": "recent"
            })
        
        # Look for other alert-worthy metrics
        total_repos = dashboard_data.get('total_repositories', 0)
        if total_repos > 50:  # Threshold could be configurable
            alerts.append({
                "id": 2,
                "type": "high_volume",
                "severity": "low",
                "message": f"Monitoring {total_repos} repositories",
                "created_at": "recent"
            })
        
        if alerts:
            table = Table(title="System Alerts")
            table.add_column("ID", style="dim")
            table.add_column("Type")
            table.add_column("Severity")
            table.add_column("Message")
            table.add_column("Created")
            
            for alert in alerts:
                severity_color = "[red]" if alert['severity'] == 'high' else "[yellow]" if alert['severity'] == 'medium' else "[green]"
                table.add_row(
                    str(alert['id']),
                    alert['type'],
                    f"{severity_color}{alert['severity']}[/]",
                    alert['message'],
                    alert['created_at']
                )
            
            console.print(table)
        else:
            console.print("[green]No active system alerts[/green]")
    else:
        # Fallback to mock data
        console.print("[yellow]Note: Alert API not available, showing mock data[/yellow]")
        alerts = [
            {
                "id": 1,
                "type": "stale_claim",
                "severity": "high",
                "message": "Claim on issue #123 has been inactive for 10 days",
                "created_at": "2024-01-01T09:00:00Z"
            },
            {
                "id": 2,
                "type": "high_claim_volume",
                "severity": "medium",
                "message": "Unusual number of claims on repo org/repo1",
                "created_at": "2024-01-01T08:30:00Z"
            }
        ]
        
        table = Table(title="System Alerts")
        table.add_column("ID", style="dim")
        table.add_column("Type")
        table.add_column("Severity")
        table.add_column("Message")
        table.add_column("Created")
        
        for alert in alerts:
            severity_color = "[red]" if alert['severity'] == 'high' else "[yellow]" if alert['severity'] == 'medium' else "[green]"
            table.add_row(
                str(alert['id']),
                alert['type'],
                f"{severity_color}{alert['severity']}[/]",
                alert['message'],
                alert['created_at'].split('T')[0]
            )
        
        console.print(table)