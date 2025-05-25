#!/bin/bash
# Build and install the UniCache package

set -e

echo "Building UniCache package..."

# Make sure maturin is installed
if ! command -v maturin &> /dev/null; then
    echo "Installing maturin..."
    pip install maturin
fi

# Build the package in development mode
echo "Building package in development mode..."
maturin develop

echo "UniCache has been built and installed successfully!"
echo "You can now use the 'unicache' command or import the library in Python."
echo ""
echo "Try running one of the examples:"
echo "  python examples/basic_example.py"
echo "  python examples/download_example.py"
echo "  python examples/benchmark.py"
echo ""
echo "Or use the command line tool:"
echo "  unicache --help" 