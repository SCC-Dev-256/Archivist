"""Generate comprehensive Markdown documentation from module docstrings.

This script parses Python modules in the ``core`` package and extracts the
module-level docstrings. The collected documentation is written to
``docs/modules.md``. It includes module descriptions, key features, and usage
examples.

The generated documentation follows a consistent format:
- Module name and description
- Key features list
- Usage examples
- Dependencies and requirements
"""

from __future__ import annotations

import ast
from pathlib import Path
from datetime import datetime


def extract_docstring(path: Path) -> str:
    """Return the module level docstring for *path* or an empty string."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    doc = ast.get_docstring(tree)
    return doc or ""


def generate_docs(package_dir: str = "core", output_file: str = "docs/modules.md") -> None:
    """Generate documentation for all modules in ``package_dir``.

    Parameters
    ----------
    package_dir : str
        Directory containing the package to document.
    output_file : str
        Path of the Markdown file to write.
    """
    root = Path(__file__).resolve().parent.parent
    package_path = root / package_dir
    
    # Generate header with timestamp
    lines = [
        "# Module Documentation\n",
        f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        "This documentation is automatically generated from module docstrings.\n",
        "## Table of Contents\n"
    ]
    
    # First pass to collect module names for TOC
    modules = []
    for py in sorted(package_path.rglob("*.py")):
        module = py.relative_to(root).with_suffix("")
        module_name = ".".join(module.parts)
        modules.append(module_name)
        lines.append(f"- [{module_name}](#{module_name.lower().replace('.', '')})")
    
    lines.append("\n## Modules\n")
    
    # Second pass to generate detailed documentation
    for py in sorted(package_path.rglob("*.py")):
        module = py.relative_to(root).with_suffix("")
        module_name = ".".join(module.parts)
        doc = extract_docstring(py)
        
        lines.append(f"### {module_name}\n")
        if doc:
            lines.append(doc + "\n")
        else:
            lines.append("No documentation available.\n")
        
        # Add module dependencies
        with open(py, 'r') as f:
            content = f.read()
            imports = [line.strip() for line in content.split('\n') 
                      if line.strip().startswith(('import ', 'from '))]
            if imports:
                lines.append("#### Dependencies\n")
                for imp in imports:
                    lines.append(f"- {imp}\n")
    
    Path(output_file).write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    generate_docs() 