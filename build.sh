#!/bin/bash
set -e

# Create a custom directory
mkdir -p /decodelibs/

# Install additional dependencies if needed directly via apt-get
apt-get update
apt-get install -y libopus0 ffmpeg

# Example of moving files, if needed
# This is more symbolic as libopus0 and ffmpeg don't typically need to be moved.
# cp /usr/lib/libopus.so* /custom/dir/
