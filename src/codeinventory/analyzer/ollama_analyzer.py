import json
import requests
from typing import Dict, Optional
from codeinventory.scanner.enhanced_scanner import EnhancedAnalyzer

class OllamaAnalyzer:
    def __init__(self, config: Dict):
        self.host = config['analyzer']['ollama']['host']
        self.model = config['analyzer']['ollama']['model']
        self.temperature = config['analyzer']['ollama']['temperature']
        self.timeout = config['analyzer']['timeout']
        self.enhanced_analyzer = EnhancedAnalyzer()

    def analyze(self, file_info: Dict) -> Optional[Dict]:
        """Analyze file content using Ollama."""
        prompt = self._create_prompt(file_info['content'], file_info['language'])
        
        try:
            response = requests.post(
                f"{self.host}/api/generate",
                json={
                    'model': self.model,
                    'prompt': prompt,
                    'stream': False,
                    'format': 'json'
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                try:
                    ai_analysis = json.loads(result['response'])
                    
                    # Add enhanced analysis
                    enhanced_info = self.enhanced_analyzer.analyze_file(
                        file_info['path'],
                        file_info['content'],
                        file_info['language']
                    )
                    
                    # Merge the results
                    ai_analysis.update(enhanced_info)
                    
                    return ai_analysis
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    return None
            else:
                print(f"Ollama error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Analysis error: {e}")
            return None
    
    def _create_prompt(self, content: str, language: str) -> str:
        """Create analysis prompt."""
        return f"""Analyze this {language} code and respond with a JSON object containing:
{{
    "purpose": "one-line summary of what this code does",
    "description": "detailed description",
    "category": "choose from: file-ops, api, ui, data-processing, utility, build, test, config",
    "complexity": "simple, moderate, or complex",
    "components": [
        {{
            "name": "function or class name",
            "type": "function|class|method",
            "purpose": "what this component does",
            "signature": "function signature"
        }}
    ],
    "dependencies": ["list of imports and external dependencies"],
    "examples": ["usage examples if apparent from code"],
    "improvements": ["potential improvements or issues"]
}}

Code to analyze:
{content}

Respond ONLY with valid JSON."""
