import sys
import time
from pathlib import Path
sys.path.insert(0, '/Users/markpiesner/Documents/GitHub/codeinventory/src')

from codeinventory.cli.cli import load_config
from codeinventory.scanner.scanner import Scanner
from codeinventory.analyzer.ollama_analyzer import OllamaAnalyzer
from codeinventory.database.db import InventoryDB
import yaml

def main():
    # Create a custom config that excludes the massive directories
    custom_config = {
        'scanner': {
            'exclude': [
                "__pycache__", ".git", "node_modules", "venv", ".venv", "build", "dist",
                "desktopbuddy", "keechprep", "TimeEntrySumarizer", "time-entry-system",
                "advanced-activity-tracker", "activity-tracker", "CountPages", "FinAnalysis",
                "sandbox", "*.pyc", ".DS_Store", "*.egg-info"
            ],
            'max_file_size': 524288,  # 512KB
            'extensions': {
                'python': [".py"],
                'javascript': [".js", ".jsx", ".ts", ".tsx"],
                'shell': [".sh", ".bash", ".zsh"]
            }
        },
        'analyzer': {
            'ollama': {
                'host': "http://localhost:11434",
                'model': "codellama",
                'temperature': 0.3
            },
            'timeout': 15
        },
        'database': {
            'path': "~/.codeinventory/inventory.db"
        }
    }
    
    scanner = Scanner(custom_config)
    analyzer = OllamaAnalyzer(custom_config)
    db = InventoryDB(custom_config['database']['path'])
    
    # Only scan the smaller, relevant directories
    small_dirs = [
        'rag', 'ai_analysis', 'newClient', 'activity-tracker-mirror',
        'legaldocumentsystem', 'OpenManus'
    ]
    
    all_files = []
    for dir_name in small_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"Scanning {dir_name}...")
            files = list(scanner.scan(dir_path))
            all_files.extend(files)
            print(f"  Found {len(files)} files")
    
    # Also scan root level files
    print("Scanning root level files...")
    root_files = []
    for f in Path('.').iterdir():
        if f.is_file() and f.suffix in ['.py', '.js', '.sh', '.jsx', '.ts', '.tsx']:
            try:
                file_info = scanner._get_file_info(f)
                if file_info:
                    root_files.append(file_info)
            except:
                pass
    all_files.extend(root_files)
    print(f"  Found {len(root_files)} root files")
    
    print(f"\nTotal files to analyze: {len(all_files)}")
    
    analyzed_count = 0
    error_count = 0
    skip_count = 0
    start_time = time.time()
    
    for i, file_info in enumerate(all_files):
        if i % 5 == 0:  # Update more frequently
            elapsed = time.time() - start_time
            rate = analyzed_count / elapsed if elapsed > 0 else 0
            print(f"\nProgress: {i}/{len(all_files)} files ({i/len(all_files)*100:.1f}%)")
            print(f"Analyzed: {analyzed_count}, Skipped: {skip_count}, Errors: {error_count}")
            print(f"Time elapsed: {elapsed:.1f}s, Rate: {rate:.1f} files/s")
            if rate > 0:
                remaining = (len(all_files) - i) / rate
                print(f"Estimated time remaining: {remaining:.1f}s")
        
        # Skip very large files
        if file_info.get('size', 0) > 524288:  # 512KB
            print(f"Skipping large file: {file_info['name']} ({file_info['size']} bytes)")
            skip_count += 1
            continue
            
        print(f"Analyzing: {file_info['name']}...", end='', flush=True)
        
        try:
            analysis = analyzer.analyze(file_info)
            if analysis:
                tool_id = db.save_tool(file_info, analysis)
                if tool_id:
                    purpose = analysis.get('purpose', 'Unknown')
                    print(f" Done! Purpose: {purpose[:50]}...")
                    analyzed_count += 1
                else:
                    print(" Failed to save")
                    error_count += 1
            else:
                print(" No analysis returned")
                error_count += 1
        except KeyboardInterrupt:
            print("\n\nScan interrupted by user")
            break
        except Exception as e:
            print(f" Error: {e}")
            error_count += 1
    
    elapsed = time.time() - start_time
    print(f"\n\nScan completed!")
    print(f"Total files: {len(all_files)}")
    print(f"Successfully analyzed: {analyzed_count}")
    print(f"Skipped: {skip_count}")
    print(f"Errors: {error_count}")
    print(f"Time taken: {elapsed:.1f}s")
    if analyzed_count > 0:
        print(f"Average rate: {analyzed_count/elapsed:.2f} files/s")

if __name__ == '__main__':
    main()
