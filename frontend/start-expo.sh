#!/bin/bash
# Start Expo with both web and tunnel support for Expo Go

cd /app/frontend

# Start expo with tunnel (supports both web and Expo Go)
exec yarn expo start --tunnel --port 3000
