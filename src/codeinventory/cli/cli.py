import click
import yaml
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

from ..scanner.scanner import Scanner
from ..analyzer.ollama_analyzer import OllamaAnalyzer
from ..database.db import InventoryDB

console = Console()

def load_config():
    """Load configuration file."""
    config_path = Path(__file__).parent.parent / 'config' / 'default.yaml'
    with open(config_path) as f:
        return yaml.safe_load(f)

@click.group()
def cli():
    """CodeInventory - AI-powered code inventory system."""
    pass

@cli.command()
@click.argument('directory', type=click.Path(exists=True))
@click.option('--recursive', '-r', is_flag=True, help='Scan recursively')
def scan(directory, recursive):
    """Scan directory and analyze code."""
    config = load_config()
    
    with console.status("[bold green]Initializing...") as status:
        scanner = Scanner(config)
        analyzer = OllamaAnalyzer(config)
        db = InventoryDB(config['database']['path'])
    
    console.print(f"[green]Scanning {directory}...")
    files = scanner.scan(directory)
    console.print(f"[blue]Found {len(files)} files to analyze")
    
    with Progress() as progress:
        task = progress.add_task("[cyan]Analyzing files...", total=len(files))
        
        for file_info in files:
            console.print(f"Analyzing [yellow]{file_info['name']}[/yellow]...")
            
            analysis = analyzer.analyze(file_info)
            
            if analysis:
                tool_id = db.save_tool(file_info, analysis)
                console.print(f"[green]✓[/green] {file_info['name']}: {analysis.get('purpose', 'No purpose found')}")
            else:
                console.print(f"[red]✗[/red] {file_info['name']}: Analysis failed")
            
            progress.update(task, advance=1)
    
    db.close()
    console.print("[bold green]Scan complete!")

@cli.command()
@click.argument('query')
def search(query):
    """Search the code inventory."""
    config = load_config()
    db = InventoryDB(config['database']['path'])
    
    results = db.search(query)
    
    if not results:
        console.print("[yellow]No results found[/yellow]")
        return
    
    table = Table(title=f"Search Results for '{query}'")
    table.add_column("Name", style="cyan")
    table.add_column("Purpose", style="green")
    table.add_column("Category", style="yellow")
    table.add_column("Path", style="blue")
    
    for tool in results:
        table.add_row(
            tool['name'],
            tool.get('purpose', 'N/A'),
            tool.get('category', 'N/A'),
            tool['path']
        )
    
    console.print(table)
    db.close()

@cli.command()
@click.argument('tool_id')
def show(tool_id):
    """Show detailed information about a tool."""
    config = load_config()
    db = InventoryDB(config['database']['path'])
    
    tool = db.get_tool(tool_id)
    
    if not tool:
        console.print(f"[red]Tool with ID {tool_id} not found[/red]")
        return
    
    console.print(f"[bold cyan]{tool['name']}[/bold cyan]")
    console.print(f"[green]Purpose:[/green] {tool.get('purpose', 'N/A')}")
    console.print(f"[green]Description:[/green] {tool.get('description', 'N/A')}")
    console.print(f"[green]Category:[/green] {tool.get('category', 'N/A')}")
    console.print(f"[green]Language:[/green] {tool['language']}")
    console.print(f"[green]Path:[/green] {tool['path']}")
    
    if tool.get('components'):
        console.print("\n[bold]Components:[/bold]")
        for comp in tool['components']:
            console.print(f"  - [yellow]{comp['name']}[/yellow] ({comp['type']}): {comp.get('purpose', 'N/A')}")
    
    if tool.get('dependencies'):
        console.print("\n[bold]Dependencies:[/bold]")
        for dep in tool['dependencies']:
            console.print(f"  - [blue]{dep['dependency_name']}[/blue]")
    
    db.close()

def main():
    cli()

if __name__ == '__main__':
    main()
