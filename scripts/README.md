# Automated Docstring Injection

This directory contains scripts to automatically extract docstrings from C++ source code and inject them into Python bindings.

## Overview

The script `add_docstrings.py` automates the process of transferring documentation from C++ methods to their corresponding Python bindings. It uses Doxygen to parse C++ source files and extract docstrings, then modifies the nanobind bindings to include those docstrings.

## How it works

1. **Extract from C++**: Uses Doxygen to parse C++ source files and output structured XML containing all documentation
2. **Parse XML**: Parses the Doxygen XML to create a mapping of `ClassName::MethodName` to docstring content  
3. **Update Bindings**: Scans the nanobind C++ file for `.def()` calls and adds missing docstrings
4. **Generate Stubs**: The updated bindings automatically propagate docstrings to the generated `.pyi` type stubs

## Usage

Run the script using the justfile recipe:

```bash
just add-docs
```

Or run directly:

```bash
cd scripts
python3 add_docstrings.py
```

## Files

- `Doxyfile` - Doxygen configuration to extract docs from MMCore C++ source
- `add_docstrings.py` - Main script that handles the extraction and injection
- `pyproject.toml` - Dependencies for the script (lxml)

## Dependencies

- `doxygen` - Must be installed on the system
- `lxml` - Python XML parsing library (auto-installed by script)

## Integration

This script can be run as part of your development workflow to keep Python docstrings synchronized with C++ documentation. Consider running it:

- After updating the C++ source code
- Before generating releases
- As part of your CI/CD pipeline

The script is idempotent - it won't add duplicate docstrings to methods that already have them.
