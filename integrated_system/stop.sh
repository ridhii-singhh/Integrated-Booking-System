#!/bin/bash
# Stop script for Integrated Booking & Calling System

set -e

echo "🛑 Stopping Integrated Booking & Calling System..."

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to kill process by PID
kill_process() {
    local pid=$1
    local name=$2
    
    if [ -z "$pid" ]; then
        return
    fi
    
    if kill -0 $pid 2>/dev/null; then
        print_status "Stopping $name (PID: $pid)..."
        kill $pid 2>/dev/null || true
        
        # Wait for graceful shutdown
        local count=0
        while kill -0 $pid 2>/dev/null && [ $count -lt 10 ]; do
            sleep 1
            ((count++))
        done
        
        # Force kill if still running
        if kill -0 $pid 2>/dev/null; then
            print_warning "Force killing $name (PID: $pid)..."
            kill -9 $pid 2>/dev/null || true
        fi
        
        print_success "$name stopped"
    else
        print_warning "$name (PID: $pid) was not running"
    fi
}

# Function to kill process by port
kill_by_port() {
    local port=$1
    local name=$2
    
    local pid=$(lsof -ti:$port 2>/dev/null || true)
    if [ ! -z "$pid" ]; then
        print_status "Found $name on port $port (PID: $pid)"
        kill_process $pid $name
    fi
}

# Try to read PIDs from files first
if [ -f "logs/all_pids.txt" ]; then
    print_status "Reading PIDs from log files..."
    source logs/all_pids.txt
    
    kill_process $BOOKING_PID "Booking Agent"
    kill_process $CALLING_PID "Calling Agent" 
    kill_process $ORCHESTRATOR_PID "Orchestrator"
else
    print_warning "PID files not found, trying to kill by port..."
fi

# Also try to kill by individual PID files
for service in booking_agent calling_agent orchestrator; do
    if [ -f "logs/${service}.pid" ]; then
        pid=$(cat "logs/${service}.pid")
        service_name=$(echo $service | sed 's/_/ /g' | sed 's/\b\w/\u&/g')
        kill_process $pid "$service_name"
    fi
done

# Kill any remaining processes on known ports
print_status "Checking for remaining processes on ports..."
kill_by_port 8000 "Booking Agent"
kill_by_port 8001 "Calling Agent"
kill_by_port 8080 "Orchestrator"

# Clean up PID files
print_status "Cleaning up PID files..."
rm -f logs/*.pid logs/all_pids.txt

# Show final status
echo ""
echo "======================================================"
print_success "🎉 All services stopped successfully!"
echo "======================================================"
echo ""
echo "📁 Log files are still available in the logs/ directory:"
echo "   logs/booking_agent.log"
echo "   logs/calling_agent.log"
echo "   logs/orchestrator.log"
echo ""
echo "🚀 To start the system again, run: ./start.sh"