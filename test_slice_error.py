#!/usr/bin/env python3
# Test to reproduce "unhashable type: 'slice'" error

# The error happens when Python interprets something as trying to create a set with a slice object

# This is the pattern that causes the error:
try:
    # When you write {something[:10]} Python thinks you want a set containing a slice
    # But it needs to evaluate the slice first
    result = {slice(None, 10)}  # Direct slice object
except TypeError as e:
    print(f"✓ Found the error pattern 1: {e}")

# Another way this can happen:
try:
    # If html is undefined, Python sees {:10000} as a slice literal
    result = eval("{html[:10000]}")  # This will fail if html is not defined
except Exception as e:
    print(f"✓ Found the error pattern 2: {type(e).__name__}: {e}")

# The most likely scenario in the actual code:
# Someone wrote {html[:10000]} instead of f"{html[:10000]}" or html[:10000]
# This creates ambiguity - is it a set literal or something else?

# Let's check the actual prompts.py file
print("\nNow let's check the actual prompts.py file for this pattern...")