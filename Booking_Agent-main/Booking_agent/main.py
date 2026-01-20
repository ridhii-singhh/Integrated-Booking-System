import nest_asyncio
from src.agent import app

def main():
    nest_asyncio.apply()
    
    while True:
        command = input("Enter your booking command (or 'exit' to quit): ")
        if command.lower() == 'exit':
            break
        
        initial_state = {"command": command}
        final_state = app.invoke(initial_state)
        
        print(final_state.get("final_response", "An unexpected error occurred."))

if __name__ == "__main__":
    main() 