#!/bin/bash
# Test runner for vastcat
# Runs all local tests without requiring GPU or hashcat execution

set -e

echo "================================"
echo "VastCat Test Suite"
echo "================================"
echo ""

# Run hash detection tests
echo "Running hash detection tests..."
python3 tests/test_hash_detection.py
echo ""

# Run hashcat installation tests
echo "Running hashcat installation tests..."
python3 tests/test_hashcat_install.py
echo ""

echo "================================"
echo "All tests completed!"
echo "================================"
