#!/usr/bin/env python3
# encoder.py - given to players
# This is the exact script that produced output.txt
# The original flag was passed through this function.

def custom_encode(s):
    key = 0x5A
    encoded = bytes([(b ^ key) + (i % 5) for i, b in enumerate(s.encode())])
    return encoded[::-1].hex()

if __name__ == "__main__":
    flag = input("Enter flag to encode: ")
    print(custom_encode(flag))
