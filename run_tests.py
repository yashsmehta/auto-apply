#!/usr/bin/env python3
"""Test runner for auto-apply project"""
import sys
import pytest

if __name__ == "__main__":
    # Run all tests with coverage
    args = [
        "--verbose",
        "--cov=core",
        "--cov=cli", 
        "--cov-report=term-missing",
        "tests/"
    ]
    
    # Add any additional arguments passed from command line
    args.extend(sys.argv[1:])
    
    sys.exit(pytest.main(args))