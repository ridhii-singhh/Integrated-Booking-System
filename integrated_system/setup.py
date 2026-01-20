"""
Setup script for the Integrated Booking & Calling System
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"📝 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False

def create_directory_structure():
    """Create necessary directories"""
    directories = [
        "orchestrator/logs",
        "orchestrator/data",
        "enhanced_calling_agent/logs",
        "shared/auth",
        "shared/config"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"📁 Created directory: {directory}")

def setup_virtual_environment():
    """Setup virtual environment for the project"""
    if not os.path.exists("venv"):
        if not run_command("python -m venv venv", "Creating virtual environment"):
            return False
    
    # Activate and install dependencies
    if sys.platform == "win32":
        activate_cmd = "venv\\Scripts\\activate"
        pip_cmd = "venv\\Scripts\\pip"
    else:
        activate_cmd = "source venv/bin/activate"
        pip_cmd = "venv/bin/pip"
    
    commands = [
        f"{pip_cmd} install --upgrade pip",
        f"{pip_cmd} install -r orchestrator/requirements.txt",
        f"{pip_cmd} install -r ../Booking_Agent-main/Booking_agent_api/requirements.txt",
        f"{pip_cmd} install -r ../Final-Caller_Agent-main/Caller_Agent/requirements.txt"
    ]
    
    for cmd in commands:
        if not run_command(cmd, f"Installing dependencies: {cmd}"):
            return False
    
    return True

def copy_configuration_files():
    """Copy and setup configuration files"""
    # Copy .env template
    if not os.path.exists(".env"):
        shutil.copy(".env.template", ".env")
        print("📄 Created .env file from template - please edit with your credentials")
    
    # Create orchestrator config
    config_content = """
# Orchestrator specific configuration
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# SQLite database path
SQLITE_DB_PATH = DATA_DIR / "integrated_system.db"
"""
    
    with open("orchestrator/local_config.py", "w") as f:
        f.write(config_content)
    
    print("📄 Created orchestrator local configuration")

def setup_database():
    """Setup initial database"""
    print("🗄️ Setting up database...")
    # Database will be created automatically when the app starts
    print("✅ Database setup will be handled on first run")

def create_startup_scripts():
    """Create startup scripts for different components"""
    
    # Main startup script
    startup_script = """#!/bin/bash
# Integrated Booking & Calling System Startup Script

echo "🚀 Starting Integrated Booking & Calling System..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup.py first."
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please copy .env.template to .env and configure it."
    exit 1
fi

# Source virtual environment
source venv/bin/activate

# Start services in background
echo "📅 Starting Booking Agent..."
cd ../Booking_Agent-main/Booking_agent_api
python app.py &
BOOKING_PID=$!
cd ../../integrated_system

echo "📞 Starting Enhanced Calling Agent..."
cd enhanced_calling_agent
python app.py &
CALLING_PID=$!
cd ..

echo "🔧 Starting Orchestrator..."
cd orchestrator
python main.py &
ORCHESTRATOR_PID=$!
cd ..

echo "✅ All services started!"
echo "📅 Booking Agent: PID $BOOKING_PID (http://localhost:8000)"
echo "📞 Calling Agent: PID $CALLING_PID (http://localhost:8001)"
echo "🔧 Orchestrator: PID $ORCHESTRATOR_PID (http://localhost:8080)"
echo ""
echo "🌐 Open http://localhost:8080 to access the web interface"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for user interrupt
trap 'echo "🛑 Stopping services..."; kill $BOOKING_PID $CALLING_PID $ORCHESTRATOR_PID; exit' SIGINT
wait
"""
    
    with open("start.sh", "w") as f:
        f.write(startup_script)
    
    # Make executable
    os.chmod("start.sh", 0o755)
    
    # Windows batch file
    windows_script = """@echo off
echo 🚀 Starting Integrated Booking & Calling System...

REM Check if virtual environment exists
if not exist "venv" (
    echo ❌ Virtual environment not found. Please run setup.py first.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist ".env" (
    echo ❌ .env file not found. Please copy .env.template to .env and configure it.
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\\Scripts\\activate

REM Start services
echo 📅 Starting Booking Agent...
start "Booking Agent" cmd /k "cd ..\\Booking_Agent-main\\Booking_agent_api && python app.py"

echo 📞 Starting Enhanced Calling Agent...
start "Calling Agent" cmd /k "cd enhanced_calling_agent && python app.py"

echo 🔧 Starting Orchestrator...
start "Orchestrator" cmd /k "cd orchestrator && python main.py"

echo ✅ All services started!
echo 🌐 Open http://localhost:8080 to access the web interface
pause
"""
    
    with open("start.bat", "w") as f:
        f.write(windows_script)
    
    print("📜 Created startup scripts: start.sh (Linux/Mac) and start.bat (Windows)")

def verify_setup():
    """Verify the setup is correct"""
    print("🔍 Verifying setup...")
    
    required_files = [
        ".env.template",
        "orchestrator/main.py",
        "orchestrator/requirements.txt",
        "enhanced_calling_agent/app.py",
        "start.sh",
        "start.bat"
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required files present")
    return True

def main():
    """Main setup function"""
    print("🔧 Setting up Integrated Booking & Calling System")
    print("=" * 50)
    
    # Step 1: Create directory structure
    create_directory_structure()
    
    # Step 2: Setup virtual environment
    if not setup_virtual_environment():
        print("❌ Failed to setup virtual environment")
        return
    
    # Step 3: Copy configuration files
    copy_configuration_files()
    
    # Step 4: Setup database
    setup_database()
    
    # Step 5: Create startup scripts
    create_startup_scripts()
    
    # Step 6: Verify setup
    if not verify_setup():
        print("❌ Setup verification failed")
        return
    
    print("\n" + "=" * 50)
    print("✅ Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Edit .env file with your Google and Twilio credentials")
    print("2. Set up ngrok for webhook URLs (if using Twilio)")
    print("3. Run './start.sh' (Linux/Mac) or 'start.bat' (Windows) to start all services")
    print("4. Open http://localhost:8080 to access the web interface")
    print("\n📖 For detailed setup instructions, see README.md")

if __name__ == "__main__":
    main()