#!/usr/bin/env python3
"""
Dependency Management Script

This script helps manage Python dependencies using pipdeptree to:
1. Analyze dependency trees
2. Find conflicts
3. Generate dependency graphs
4. Update requirements files
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import re
from packaging import version
from packaging.specifiers import SpecifierSet

def run_pipdeptree(args: List[str]) -> str:
    """Run pipdeptree with given arguments and return output."""
    try:
        result = subprocess.run(
            ["pipdeptree"] + args,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running pipdeptree: {e.stderr}", file=sys.stderr)
        sys.exit(1)

def get_dependency_tree() -> Dict:
    """Get the full dependency tree as JSON."""
    output = run_pipdeptree(["--json"])
    return json.loads(output)

def find_conflicts() -> List[str]:
    """Find dependency conflicts in the current environment."""
    output = run_pipdeptree(["--warn", "fail"])
    conflicts = []
    for line in output.splitlines():
        if "WARNING" in line:
            conflicts.append(line.strip())
    return conflicts

def generate_dependency_graph(output_file: str) -> None:
    """Generate a dependency graph visualization."""
    # First generate the graph in dot format
    run_pipdeptree(["--graph-output", "dot"])
    
    # Then convert to PNG using dot
    try:
        subprocess.run(
            ["dot", "-Tpng", "-o", output_file],
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error generating graph: {e}", file=sys.stderr)
        sys.exit(1)

def get_installed_packages() -> Dict[str, str]:
    """Get a dictionary of installed package names and versions."""
    output = run_pipdeptree(["--json-tree"])
    packages = {}
    
    def extract_packages(data):
        if isinstance(data, dict):
            if "key" in data and "installed_version" in data:
                packages[data["key"]] = data["installed_version"]
            for value in data.values():
                extract_packages(value)
        elif isinstance(data, list):
            for item in data:
                extract_packages(item)
    
    try:
        data = json.loads(output)
        extract_packages(data)
    except json.JSONDecodeError as e:
        print(f"Error parsing pipdeptree output: {e}", file=sys.stderr)
        sys.exit(1)
    
    return packages

def parse_requirements_file(req_file: Path) -> Dict[str, str]:
    """Parse a requirements file and return package constraints."""
    constraints = {}
    with open(req_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('-r'):
                # Handle recursive requirements
                sub_file = req_file.parent / line[3:].strip()
                constraints.update(parse_requirements_file(sub_file))
                continue
            
            # Parse package and version constraint
            match = re.match(r'^([a-zA-Z0-9_.-]+)([<>=!~].*)?$', line)
            if match:
                pkg, ver = match.groups()
                constraints[pkg] = ver.strip() if ver else None
    return constraints

def check_version_conflicts(installed: Dict[str, str], constraints: Dict[str, str]) -> List[str]:
    """Check for version conflicts between installed packages and constraints."""
    conflicts = []
    for pkg, constraint in constraints.items():
        if pkg not in installed:
            continue
        if not constraint:
            continue
        # Remove inline comments from constraint
        constraint_clean = constraint.split('#')[0].strip()
        try:
            spec_set = SpecifierSet(constraint_clean)
            if not spec_set.contains(installed[pkg]):
                conflicts.append(f"{pkg}: installed {installed[pkg]} does not satisfy constraint {constraint_clean}")
        except Exception as e:
            conflicts.append(f"{pkg}: error parsing constraint '{constraint_clean}' or version '{installed[pkg]}': {e}")
    return conflicts

def analyze_requirements_file(req_file: Path) -> Tuple[Set[str], Set[str], List[str]]:
    """Analyze a requirements file for potential issues."""
    with open(req_file) as f:
        requirements = {line.strip() for line in f if line.strip() and not line.startswith("#")}
    
    # Get installed packages
    installed_packages = get_installed_packages()
    
    # Parse requirements file
    constraints = parse_requirements_file(req_file)
    
    # Find missing and outdated packages
    missing = set(constraints.keys()) - set(installed_packages.keys())
    outdated = set()  # This would require additional logic to check versions
    
    # Check version conflicts
    conflicts = check_version_conflicts(installed_packages, constraints)
    
    return missing, outdated, conflicts

def update_requirements_file(req_file: Path, missing: Set[str], outdated: Set[str], conflicts: List[str]) -> None:
    """Update requirements file with missing and outdated packages."""
    if not missing and not outdated and not conflicts:
        print(f"No updates needed for {req_file}")
        return
    
    with open(req_file, 'r') as f:
        lines = f.readlines()
    
    with open(req_file, 'w') as f:
        for line in lines:
            if line.strip() and not line.startswith('#'):
                pkg = line.split('==')[0].split('>=')[0].strip()
                if pkg in missing:
                    f.write(f"{pkg}>=0.0.0  # Added by dependency manager\n")
                elif pkg in outdated:
                    f.write(f"{pkg}>=0.0.0  # Updated by dependency manager\n")
                else:
                    f.write(line)
            else:
                f.write(line)
        
        if conflicts:
            f.write("\n# Version conflicts detected:\n")
            for conflict in conflicts:
                f.write(f"# {conflict}\n")

def main():
    parser = argparse.ArgumentParser(description="Manage Python dependencies")
    parser.add_argument("--analyze", action="store_true", help="Analyze dependencies")
    parser.add_argument("--conflicts", action="store_true", help="Find conflicts")
    parser.add_argument("--graph", help="Generate dependency graph (output file)")
    parser.add_argument("--update", help="Update requirements file")
    parser.add_argument("--check", help="Check requirements file for issues")
    
    args = parser.parse_args()
    
    if args.analyze:
        tree = get_dependency_tree()
        print(json.dumps(tree, indent=2))
    
    if args.conflicts:
        conflicts = find_conflicts()
        if conflicts:
            print("Found conflicts:")
            for conflict in conflicts:
                print(f"  {conflict}")
        else:
            print("No conflicts found")
    
    if args.graph:
        generate_dependency_graph(args.graph)
        print(f"Dependency graph generated: {args.graph}")
    
    if args.check:
        req_file = Path(args.check)
        if not req_file.exists():
            print(f"Requirements file not found: {req_file}")
            sys.exit(1)
        
        missing, outdated, conflicts = analyze_requirements_file(req_file)
        if missing or outdated or conflicts:
            print(f"Issues found in {req_file}:")
            if missing:
                print("\nMissing packages:")
                for pkg in missing:
                    print(f"  {pkg}")
            if outdated:
                print("\nOutdated packages:")
                for pkg in outdated:
                    print(f"  {pkg}")
            if conflicts:
                print("\nVersion conflicts:")
                for conflict in conflicts:
                    print(f"  {conflict}")
        else:
            print(f"No issues found in {req_file}")
    
    if args.update:
        req_file = Path(args.update)
        if not req_file.exists():
            print(f"Requirements file not found: {req_file}")
            sys.exit(1)
        
        missing, outdated, conflicts = analyze_requirements_file(req_file)
        if missing or outdated or conflicts:
            print(f"Updating {req_file}")
            update_requirements_file(req_file, missing, outdated, conflicts)
        else:
            print(f"No updates needed for {req_file}")

if __name__ == "__main__":
    main() 