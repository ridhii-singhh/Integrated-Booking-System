#!/bin/bash
# Integrated Booking & Calling System Startup Script

set -e  # Exit on any error

echo "🚀 Starting Integrated Booking & Calling System..."
echo "======================================================"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Check if we're in the right directory
if [ ! -f "orchestrator/main.py" ]; then
    print_error "Please run this script from the integrated_system directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_error "Virtual environment not found. Please run setup.py first."
    print_status "Run: python setup.py"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found. Please copy .env.template to .env and configure it."
    print_status "Run: cp .env.template .env && nano .env"
    exit 1
fi

# Source virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to find and kill process on port
kill_port() {
    local port=$1
    local pid=$(lsof -ti:$port)
    if [ ! -z "$pid" ]; then
        print_warning "Killing existing process on port $port (PID: $pid)"
        kill -9 $pid 2>/dev/null || true
        sleep 1
    fi
}

# Check and clean up ports
PORTS=(8000 8001 8080)
for port in "${PORTS[@]}"; do
    if check_port $port; then
        kill_port $port
    fi
done

# Create log directory
mkdir -p logs

# Start services with proper error handling
print_status "Starting Booking Agent..."
cd ../Booking_Agent-main/Booking_agent_api
nohup python app.py > ../../integrated_system/logs/booking_agent.log 2>&1 &
BOOKING_PID=$!
cd ../../integrated_system
echo $BOOKING_PID > logs/booking_agent.pid
print_success "Booking Agent started (PID: $BOOKING_PID)"

# Wait a moment for the service to start
sleep 2

print_status "Starting Enhanced Calling Agent..."
cd enhanced_calling_agent
nohup python app.py > ../logs/calling_agent.log 2>&1 &
CALLING_PID=$!
cd ..
echo $CALLING_PID > logs/calling_agent.pid
print_success "Enhanced Calling Agent started (PID: $CALLING_PID)"

# Wait a moment for the service to start
sleep 2

print_status "Starting Orchestrator..."
cd orchestrator
nohup python main.py > ../logs/orchestrator.log 2>&1 &
ORCHESTRATOR_PID=$!
cd ..
echo $ORCHESTRATOR_PID > logs/orchestrator.pid
print_success "Orchestrator started (PID: $ORCHESTRATOR_PID)"

# Wait for services to be ready
print_status "Waiting for services to initialize..."
sleep 5

# Health check function
health_check() {
    local service=$1
    local url=$2
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            print_success "$service is ready"
            return 0
        fi
        print_status "Waiting for $service... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    print_error "$service failed to start properly"
    return 1
}

# Check if services are ready
print_status "Performing health checks..."

health_check "Booking Agent" "http://localhost:8000/api/v1/health"
BOOKING_HEALTH=$?

health_check "Calling Agent" "http://localhost:8001/health"
CALLING_HEALTH=$?

health_check "Orchestrator" "http://localhost:8080/api/v1/health"
ORCHESTRATOR_HEALTH=$?

echo ""
echo "======================================================"
print_success "🎉 Integrated Booking & Calling System Started!"
echo "======================================================"
echo ""
echo "📊 Service Status:"
if [ $BOOKING_HEALTH -eq 0 ]; then
    echo -e "   📅 Booking Agent:    ${GREEN}✅ Running${NC} (http://localhost:8000)"
else
    echo -e "   📅 Booking Agent:    ${RED}❌ Failed${NC} (http://localhost:8000)"
fi

if [ $CALLING_HEALTH -eq 0 ]; then
    echo -e "   📞 Calling Agent:    ${GREEN}✅ Running${NC} (http://localhost:8001)"
else
    echo -e "   📞 Calling Agent:    ${RED}❌ Failed${NC} (http://localhost:8001)"
fi

if [ $ORCHESTRATOR_HEALTH -eq 0 ]; then
    echo -e "   🔧 Orchestrator:     ${GREEN}✅ Running${NC} (http://localhost:8080)"
else
    echo -e "   🔧 Orchestrator:     ${RED}❌ Failed${NC} (http://localhost:8080)"
fi

echo ""
echo "🌐 Access Points:"
echo "   Main Interface:    http://localhost:8080"
echo "   API Documentation: http://localhost:8080/docs"
echo ""
echo "📁 Logs:"
echo "   Booking Agent:     logs/booking_agent.log"
echo "   Calling Agent:     logs/calling_agent.log"
echo "   Orchestrator:      logs/orchestrator.log"
echo ""
echo "🛑 To stop all services, run: ./stop.sh"
echo ""

# Save all PIDs for stop script
cat > logs/all_pids.txt << EOF
BOOKING_PID=$BOOKING_PID
CALLING_PID=$CALLING_PID
ORCHESTRATOR_PID=$ORCHESTRATOR_PID
EOF

# Optional: Run integration tests
echo "🧪 Would you like to run integration tests? (y/n)"
read -t 10 -n 1 test_choice
echo ""
if [[ $test_choice == "y" || $test_choice == "Y" ]]; then
    print_status "Running integration tests..."
    python test_integration.py
else
    print_status "Skipping integration tests. You can run them later with: python test_integration.py"
fi

echo ""
print_success "System is ready! Open http://localhost:8080 to get started."

# Keep script running to show real-time logs (optional)
echo ""
echo "Press Ctrl+C to stop all services, or 'q' to quit without stopping services"
echo "Watching logs (last 10 lines from each service):"
echo "======================================================"

# Function to display logs
show_logs() {
    echo -e "\n${BLUE}📅 Booking Agent:${NC}"
    tail -n 5 logs/booking_agent.log 2>/dev/null || echo "No logs yet"
    
    echo -e "\n${BLUE}📞 Calling Agent:${NC}"
    tail -n 5 logs/calling_agent.log 2>/dev/null || echo "No logs yet"
    
    echo -e "\n${BLUE}🔧 Orchestrator:${NC}"
    tail -n 5 logs/orchestrator.log 2>/dev/null || echo "No logs yet"
    
    echo -e "\n${YELLOW}===========================================${NC}"
}

# Cleanup function
cleanup() {
    echo ""
    print_warning "Stopping all services..."
    
    # Kill processes
    for pid in $BOOKING_PID $CALLING_PID $ORCHESTRATOR_PID; do
        if kill -0 $pid 2>/dev/null; then
            print_status "Stopping process $pid..."
            kill $pid 2>/dev/null || true
        fi
    done
    
    # Wait a moment for graceful shutdown
    sleep 3
    
    # Force kill if necessary
    for pid in $BOOKING_PID $CALLING_PID $ORCHESTRATOR_PID; do
        if kill -0 $pid 2>/dev/null; then
            print_warning "Force killing process $pid..."
            kill -9 $pid 2>/dev/null || true
        fi
    done
    
    # Clean up PID files
    rm -f logs/*.pid logs/all_pids.txt
    
    print_success "All services stopped."
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Main loop
while true; do
    read -t 5 -n 1 key 2>/dev/null || true
    
    if [[ $key == "q" || $key == "Q" ]]; then
        print_status "Exiting without stopping services..."
        print_warning "Services are still running. Use ./stop.sh to stop them."
        exit 0
    fi
    
    # Show logs every 30 seconds
    if [ $(($(date +%s) % 30)) -eq 0 ]; then
        clear
        echo "🚀 Integrated Booking & Calling System - Live Status"
        echo "======================================================"
        show_logs
        echo ""
        echo "Press Ctrl+C to stop all services, or 'q' to quit without stopping"
    fi
done