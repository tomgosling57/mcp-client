from typing import Optional
from cli_chatbot.chat.history import ChatHistoryManager
from cli_chatbot.llm.interface import LLMInterface

class ChatLoop:
    """Implements the main chat loop for the CLI chatbot.
    
    Args:
        history_manager: ChatHistoryManager instance for managing message history
        llm_client: LLM client implementing LLMInterface
    """
    
    def __init__(self, history_manager: ChatHistoryManager, llm_client: LLMInterface):
        self.history_manager = history_manager
        self.llm_client = llm_client
    
    def run(self) -> None:
        """Run the main chat loop until user exits."""
        print("Chat session started. Type 'exit' or 'quit' to end.")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ('exit', 'quit'):
                    print("Exiting chat...")
                    break
                    
                if not user_input:
                    continue
                    
                self.process_message(user_input)
                
            except KeyboardInterrupt:
                print("\nExiting chat...")
                break
    
    def process_message(self, user_message: str) -> Optional[str]:
        """Process a single user message through the chat cycle.
        
        Args:
            user_message: The user's input message
            
        Returns:
            The assistant's response, or None if no response was generated
        """
        # Add user message to history
        self.history_manager.add_message("user", user_message)
        
        # Get formatted history context
        context = self.history_manager.get_context_string()
        
        # Get LLM response
        response = self.llm_client.send_message(context)
        
        # Display and store response
        print(f"Assistant: {response}")
        self.history_manager.add_message("assistant", response)
        
        return response