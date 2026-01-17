#!/usr/bin/env python3
"""
PromptMesh Setup and Diagnostic Script
Run this before starting the application to verify everything is configured correctly.
"""

import os
import sys
from pathlib import Path

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def check_file(filepath, description):
    """Check if a file exists"""
    if Path(filepath).exists():
        print(f"✓ {description}: {filepath}")
        return True
    else:
        print(f"✗ MISSING: {description}: {filepath}")
        return False

def check_directory(dirpath, description):
    """Check if a directory exists"""
    if Path(dirpath).exists() and Path(dirpath).is_dir():
        print(f"✓ {description}: {dirpath}")
        return True
    else:
        print(f"✗ MISSING: {description}: {dirpath}")
        return False

def create_static_structure():
    """Create static folder structure"""
    print_header("CREATING STATIC FOLDER STRUCTURE")
    
    static_dir = Path("static")
    static_dir.mkdir(exist_ok=True)
    print(f"✓ Created: {static_dir}")
    
    # Check for required files
    required_files = {
        "static/index.html": "Frontend HTML",
        "static/styles.css": "Stylesheet",
        "static/app.js": "JavaScript"
    }
    
    missing = []
    for filepath, desc in required_files.items():
        if not check_file(filepath, desc):
            missing.append(filepath)
    
    if missing:
        print("\n⚠️  WARNING: Missing files in static/")
        print("Please create these files:")
        for f in missing:
            print(f"  - {f}")
        return False
    
    return True

def check_dependencies():
    """Check if all Python dependencies are installed"""
    print_header("CHECKING DEPENDENCIES")
    
    required = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "jinja2",
        "pyyaml",
        "ollama",
        "oci",
        "cohere"
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ MISSING: {package}")
            missing.append(package)
    
    if missing:
        print("\n⚠️  Install missing packages:")
        print(f"pip install {' '.join(missing)}")
        return False
    
    return True

def check_project_structure():
    """Check if project structure is correct"""
    print_header("CHECKING PROJECT STRUCTURE")
    
    required_dirs = {
        "prompts/versions": "Prompt templates directory",
        "models": "Model adapters",
        "core": "Core execution",
        "evaluation": "Evaluation logic",
        "optimization": "Optimization modules",
        "comparison": "Comparison utilities"
    }
    
    missing = []
    for dirpath, desc in required_dirs.items():
        if not check_directory(dirpath, desc):
            missing.append(dirpath)
    
    required_files = {
        "app.py": "FastAPI backend",
        "prompts/registry.py": "Prompt registry",
        "models/registry.py": "Model registry"
    }
    
    for filepath, desc in required_files.items():
        if not check_file(filepath, desc):
            missing.append(filepath)
    
    if missing:
        print("\n⚠️  WARNING: Missing project files/directories")
        return False
    
    return True

def test_api_imports():
    """Test if API can import all modules"""
    print_header("TESTING API IMPORTS")
    
    try:
        from prompts.registry import PromptRegistry
        print("✓ PromptRegistry")
    except Exception as e:
        print(f"✗ PromptRegistry: {e}")
        return False
    
    try:
        from models.registry import get_model
        print("✓ Model Registry")
    except Exception as e:
        print(f"✗ Model Registry: {e}")
        return False
    
    try:
        from evaluation.scorer import evaluate
        print("✓ Evaluation Scorer")
    except Exception as e:
        print(f"✗ Evaluation Scorer: {e}")
        return False
    
    try:
        from optimization.evolver import evolve_prompt
        print("✓ Prompt Evolution")
    except Exception as e:
        print(f"✗ Prompt Evolution: {e}")
        return False
    
    return True

def create_sample_prompt():
    """Create a sample prompt for testing"""
    print_header("CREATING SAMPLE PROMPT")
    
    sample_dir = Path("prompts/versions/summarization")
    sample_dir.mkdir(parents=True, exist_ok=True)
    
    sample_file = sample_dir / "v1.yaml"
    
    if sample_file.exists():
        print(f"✓ Sample prompt already exists: {sample_file}")
        return True
    
    sample_content = """task: summarization
task_type: summarization
input_variables:
  - text
template: |
  Summarize the following text in 2-3 sentences:
  
  {{ text }}
  
  Summary:
constraints:
  temperature: 0.0
  max_tokens: 150
output_schema:
  fields:
    - summary
"""
    
    try:
        with open(sample_file, "w") as f:
            f.write(sample_content)
        print(f"✓ Created sample prompt: {sample_file}")
        return True
    except Exception as e:
        print(f"✗ Failed to create sample: {e}")
        return False

def print_startup_instructions():
    """Print instructions to start the server"""
    print_header("STARTUP INSTRUCTIONS")
    
    print("""
To start PromptMesh:

1. Make sure you're in the project root directory
2. Activate your virtual environment (if using one):
   
   Windows: venv\\Scripts\\activate
   Linux/Mac: source venv/bin/activate

3. Start the server:
   
   python app.py
   
   OR
   
   uvicorn app:app --reload --host 0.0.0.0 --port 8000

4. Open your browser to:
   
   http://localhost:8000

5. Check the browser console (F12) for any JavaScript errors

TROUBLESHOOTING:

- If you see "API Disconnected" in the UI:
  * Check that app.py is running
  * Open http://localhost:8000/api/health in browser
  * Check browser console for CORS errors

- If static files don't load:
  * Verify static/ folder exists
  * Check file paths in index.html use /static/ prefix
  * Clear browser cache (Ctrl+Shift+R)

- If models don't load:
  * For Ollama: Make sure ollama service is running
  * For OCI: Verify ociConfig/config exists
  * Check models/registry.py for correct model IDs
""")

def main():
    """Run all checks"""
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║           PromptMesh Setup Verification               ║
    ╚═══════════════════════════════════════════════════════╝
    """)
    
    checks = [
        ("Dependencies", check_dependencies),
        ("Project Structure", check_project_structure),
        ("API Imports", test_api_imports),
        ("Static Files", create_static_structure),
        ("Sample Prompt", create_sample_prompt),
    ]
    
    results = {}
    for name, check_func in checks:
        results[name] = check_func()
    
    print_header("SUMMARY")
    
    all_passed = all(results.values())
    
    for name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {name}")
    
    if all_passed:
        print("\n🎉 All checks passed! Ready to start PromptMesh.")
        print_startup_instructions()
        return 0
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())