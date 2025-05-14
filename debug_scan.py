import sys
import time
from pathlib import Path
sys.path.insert(0, 'src')

from codeinventory.cli.cli import load_config
from codeinventory.scanner.scanner import Scanner
from codeinventory.analyzer.ollama_analyzer import OllamaAnalyzer
from codeinventory.database.db import InventoryDB

def main():
    config = load_config()
    scanner = Scanner(config)
    analyzer = OllamaAnalyzer(config)
    db = InventoryDB(config['database']['path'])
    
    print("Scanning directory: .")
    files = list(scanner.scan_directory('.'))
    print(f"Found {len(files)} files to analyze")
    
    analyzed_count = 0
    start_time = time.time()
    
    for i, file_info in enumerate(files):
        if i % 10 == 0:  # Print progress every 10 files
            elapsed = time.time() - start_time
            rate = analyzed_count / elapsed if elapsed > 0 else 0
            print(f"\nProgress: {i}/{len(files)} files ({i/len(files)*100:.1f}%)")
            print(f"Time elapsed: {elapsed:.1f}s, Rate: {rate:.1f} files/s")
            if rate > 0:
                remaining = (len(files) - i) / rate
                print(f"Estimated time remaining: {remaining:.1f}s")
        
        print(f"Analyzing: {file_info['name']}...", end='', flush=True)
        
        try:
            analysis = analyzer.analyze(file_info['content'], file_info)
            tool_id = db.save_tool(file_info, analysis)
            print(f" Done! Purpose: {analysis.get('purpose', 'Unknown')[:50]}...")
            analyzed_count += 1
        except Exception as e:
            print(f" Error: {e}")

if __name__ == '__main__':
    main()
