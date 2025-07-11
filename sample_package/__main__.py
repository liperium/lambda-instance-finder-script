#!/usr/bin/env python3
"""
Lambda Cloud Instance Finder
Finds the lowest-priced available instance in us-east-1 region under $2.00/hour
Loops every 5 seconds until a good instance is found
"""

import requests
import json
import os
import dotenv
from typing import Dict, List, Optional, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from rich import box
import time
from datetime import datetime

# Initialize Rich console
console = Console()

class LambdaCloudClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://cloud.lambda.ai/api/v1"
        self.headers = {
            'accept': 'application/json'
        }
    
    def get_instance_types(self) -> Dict:
        """Fetch all available instance types from Lambda Cloud API"""
        url = f"{self.base_url}/instance-types"
        
        try:
            with Progress(
                SpinnerColumn(style="cyan"),
                TextColumn("[cyan]Fetching instance data from Lambda Cloud API..."),
                console=console
            ) as progress:
                task = progress.add_task("", total=None)
                response = requests.get(
                    url, 
                    headers=self.headers, 
                    auth=(self.api_key, '')
                )
                response.raise_for_status()
                return response.json()
        
        except requests.exceptions.RequestException as e:
            console.print(f"[red]❌ Error fetching data from API:[/red] {e}")
            return {}
    
    def find_cheapest_instance(
        self, 
        target_region: str = "us-east-1", 
        max_price_cents: int = 200
    ) -> Optional[Tuple[str, Dict]]:
        """
        Find the cheapest available instance in the target region under max price
        
        Args:
            target_region: Region to search for instances (default: us-east-1)
            max_price_cents: Maximum price in cents per hour (default: 200)
            
        Returns:
            Tuple of (instance_name, instance_data) or None if no match found
        """
        data = self.get_instance_types()
        
        if not data or 'data' not in data:
            console.print("[red]❌ No data received from API[/red]")
            return None
        
        available_instances = []
        
        with Progress(
            SpinnerColumn(style="green"),
            TextColumn("[green]🔍 Analyzing instance availability..."),
            console=console
        ) as progress:
            task = progress.add_task("", total=None)
            
            # Filter instances by region availability and price
            for instance_name, instance_info in data['data'].items():
                instance_type = instance_info.get('instance_type', {})
                regions = instance_info.get('regions_with_capacity_available', [])
                price = instance_type.get('price_cents_per_hour', float('inf'))
                
                # Check if instance is available in target region and under price limit
                region_available = any(
                    region.get('name') == target_region 
                    for region in regions
                )
                
                if region_available and price <= max_price_cents:
                    available_instances.append((instance_name, instance_info, price))
        
        if not available_instances:
            return None
        
        # Sort by price and return the cheapest
        available_instances.sort(key=lambda x: x[2])
        cheapest_name, cheapest_info, cheapest_price = available_instances[0]
        
        return cheapest_name, cheapest_info
    
    def display_instance_info(self, instance_name: str, instance_info: Dict):
        """Display formatted instance information using Rich tables and panels"""
        instance_type = instance_info['instance_type']
        specs = instance_type['specs']
        regions = instance_info['regions_with_capacity_available']
        
        # Create main info panel
        title = Text()
        title.append("🚀 ", style="cyan")
        title.append("BEST MATCH FOUND", style="bold cyan")
        title.append(" 🚀", style="cyan")
        
        instance_panel = Panel(
            f"[bold green]{instance_name}[/bold green]\n[dim]{instance_type['description']}[/dim]",
            title=title,
            border_style="cyan",
            box=box.ROUNDED
        )
        console.print(instance_panel)
        
        # Create specifications table
        spec_table = Table(title="💻 Instance Specifications", box=box.ROUNDED, title_style="bold blue")
        spec_table.add_column("🏷️  Spec", style="cyan", no_wrap=True)
        spec_table.add_column("📊 Value", style="green")
        
        spec_table.add_row("💰 Price", f"${instance_type['price_cents_per_hour']/100:.2f}/hour")
        spec_table.add_row("🎮 GPU", instance_type['gpu_description'])
        spec_table.add_row("⚡ vCPUs", str(specs['vcpus']))
        spec_table.add_row("🧠 Memory", f"{specs['memory_gib']} GiB")
        spec_table.add_row("💾 Storage", f"{specs['storage_gib']} GiB")
        spec_table.add_row("🔥 GPU Count", str(specs['gpus']))
        
        console.print(spec_table)
        
        # Create regions table
        regions_table = Table(title="🌍 Available Regions", box=box.ROUNDED, title_style="bold magenta")
        regions_table.add_column("🏁 Region", style="cyan")
        regions_table.add_column("📍 Description", style="yellow")
        
        for region in regions:
            regions_table.add_row(region['name'], region['description'])
        
        console.print(regions_table)
        
        # Success message
        success_panel = Panel(
            f"[green]✅ Found perfect match! Instance [bold]{instance_name}[/bold] is ready to launch.[/green]",
            border_style="green",
            box=box.ROUNDED
        )
        console.print(success_panel)

    def show_alternatives(self, target_region: str):
        """Show alternative instances in the region if no matches found under price limit"""
        console.print(f"\n[cyan]🔍 Checking all available instances in {target_region}...[/cyan]")
        
        all_in_region = self.find_cheapest_instance(target_region, float('inf'))
        if all_in_region:
            name, info = all_in_region
            price = info['instance_type']['price_cents_per_hour']/100
            
            alt_panel = Panel(
                f"[yellow]💡 Alternative: [bold]{name}[/bold] at [bold]${price:.2f}/hour[/bold][/yellow]",
                title="🔄 Cheapest Available in Region",
                border_style="yellow",
                box=box.ROUNDED
            )
            console.print(alt_panel)
        else:
            console.print(f"[red]❌ No instances available in {target_region}[/red]")

def print_header():
    """Print a beautiful header"""
    header = Text()
    header.append("⚡ ", style="yellow")
    header.append("LAMBDA CLOUD", style="bold cyan")
    header.append(" ☁️\n", style="cyan")
    header.append("Instance Finder", style="bold blue")
    header.append("\n🔄 Auto-Loop Mode", style="bold magenta")
    
    header_panel = Panel(
        header,
        box=box.DOUBLE,
        border_style="cyan",
        width=50,
        padding=(1, 2)
    )
    
    console.print("\n")
    console.print(header_panel, justify="center")
    console.print("\n")

def print_search_attempt(attempt: int, target_region: str, max_price: float):
    """Print search attempt information"""
    current_time = datetime.now().strftime("%H:%M:%S")
    
    attempt_text = f"[bold cyan]🔍 Search Attempt #{attempt}[/bold cyan]\n"
    attempt_text += f"[dim]⏰ Time: {current_time}[/dim]\n"
    attempt_text += f"[cyan]🎯 Region:[/cyan] [bold]{target_region}[/bold]\n"
    attempt_text += f"[cyan]💰 Max Price:[/cyan] [bold]${max_price:.2f}/hour[/bold]"
    
    attempt_panel = Panel(
        attempt_text,
        border_style="blue",
        box=box.ROUNDED,
        title="🔍 Searching..."
    )
    console.print(attempt_panel)

def print_no_match_message(attempt: int):
    """Print message when no matching instance is found"""
    retry_panel = Panel(
        f"[yellow]⚠️  No suitable instances found on attempt #{attempt}[/yellow]\n"
        f"[dim]💤 Waiting 5 seconds before next attempt...[/dim]\n"
        f"[dim]⏹️  Press Ctrl+C to stop searching[/dim]",
        title="🔄 Retrying",
        border_style="yellow",
        box=box.ROUNDED
    )
    console.print(retry_panel)

def main():
    print_header()
    
    # Get API key from environment variable
    api_key = os.getenv('LAMBDA_API_KEY')
    
    if not api_key:
        error_panel = Panel(
            "[red]❌ Missing API Key![/red]\n\n"
            "[yellow]Please set the LAMBDA_API_KEY environment variable:[/yellow]\n"
            "[cyan]export LAMBDA_API_KEY='your_secret_key_here'[/cyan]",
            title="🔑 Configuration Error",
            border_style="red",
            box=box.ROUNDED
        )
        console.print(error_panel)
        return
    
    # Initialize client
    client = LambdaCloudClient(api_key)
    
    # Configuration
    TARGET_REGION = "us-east-1"
    MAX_PRICE_CENTS = 200  # $2.00/hour
    MAX_PRICE_DOLLARS = MAX_PRICE_CENTS / 100
    
    # Loop parameters
    attempt = 0
    start_time = datetime.now()
    
    # Show initial configuration
    config_info = f"""[cyan]🎯 Target Region:[/cyan] [bold]{TARGET_REGION}[/bold]
[cyan]💰 Max Price:[/cyan] [bold]${MAX_PRICE_DOLLARS:.2f}/hour[/bold]
[cyan]🔄 Check Interval:[/cyan] [bold]5 seconds[/bold]
[cyan]⏰ Started:[/cyan] [bold]{start_time.strftime("%H:%M:%S")}[/bold]"""
    
    config_panel = Panel(
        config_info,
        title="⚙️ Configuration",
        border_style="blue",
        box=box.ROUNDED
    )
    console.print(config_panel)
    console.print()
    
    # Main search loop
    while True:
        attempt += 1
        
        # Print current attempt info
        print_search_attempt(attempt, TARGET_REGION, MAX_PRICE_DOLLARS)
        
        # Search for instances
        result = client.find_cheapest_instance(TARGET_REGION, MAX_PRICE_CENTS)
        
        if result:
            # Found a good instance!
            console.print("\n")
            elapsed_time = datetime.now() - start_time
            
            # Show success summary
            success_summary = f"[green]🎉 SUCCESS![/green]\n"
            success_summary += f"[cyan]⏱️  Total time:[/cyan] [bold]{elapsed_time.total_seconds():.1f} seconds[/bold]\n"
            success_summary += f"[cyan]🔄 Attempts:[/cyan] [bold]{attempt}[/bold]"
            
            summary_panel = Panel(
                success_summary,
                title="✅ Instance Found",
                border_style="green",
                box=box.ROUNDED
            )
            console.print(summary_panel)
            console.print()
            
            # Display the found instance
            instance_name, instance_info = result
            client.display_instance_info(instance_name, instance_info)
            
            # Return instance data for programmatic use
            return {
                'name': instance_name,
                'data': instance_info,
                'attempts': attempt,
                'elapsed_seconds': elapsed_time.total_seconds()
            }
        else:
            # No instance found, show retry message
            print_no_match_message(attempt)
            
            # Show alternatives on first attempt only
            if attempt == 1:
                client.show_alternatives(TARGET_REGION)
            
            # Wait 5 seconds before next attempt
            try:
                for i in range(5, 0, -1):
                    console.print(f"\r[dim]⏳ Next search in {i} seconds...[/dim]", end="")
                    time.sleep(1)
                console.print("\r" + " " * 50 + "\r", end="")  # Clear countdown line
                console.print()  # Add newline for next attempt
                
            except KeyboardInterrupt:
                # User pressed Ctrl+C during countdown
                raise KeyboardInterrupt

if __name__ == "__main__":
    try:
        dotenv.load_dotenv()
        result = main()
        if result:
            console.print(f"\n[dim]💡 Found {result['name']} after {result['attempts']} attempts in {result['elapsed_seconds']:.1f} seconds[/dim]")
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Search cancelled by user[/yellow]")
        elapsed = datetime.now() - datetime.now()  # This will be overwritten if we track start time
        console.print("[dim]💡 You can restart the search anytime by running the script again.[/dim]")
    except Exception as e:
        console.print(f"\n[red]💥 Unexpected error: {e}[/red]")
        console.print("[dim]Please check your API key and internet connection.[/dim]")
