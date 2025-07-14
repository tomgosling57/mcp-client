from typing import List, Dict

class ChatHistoryManager:
    """Manages chat history with configurable character limit.
    
    Args:
        max_chars: Maximum allowed characters in history (default: 2000)
    """
    
    def __init__(self, max_chars: int = 2000):
        self.max_chars = max_chars
        self.messages: List[Dict[str, str]] = []
        self._current_chars = 0

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the history.
        
        Args:
            role: 'user' or 'assistant'
            content: The message content
        """
        message = {"role": role, "content": content}
        message_chars = len(content)
        
        # Add new message
        self.messages.append(message)
        self._current_chars += message_chars
        
        # Trim oldest messages if over limit
        while self._current_chars > self.max_chars and len(self.messages) > 1:
            removed = self.messages.pop(0)
            self._current_chars -= len(removed["content"])
            
        # Handle case where single message exceeds max_chars
        if self._current_chars > self.max_chars and len(self.messages) == 1:
            self.messages[0]["content"] = self.messages[0]["content"][:self.max_chars]
            self._current_chars = self.max_chars

    def get_context_string(self) -> str:
        """Format the history into a string suitable for LLM context.
        
        Returns:
            String with messages in format "role: content" separated by newlines
        """
        return "\n".join(
            f"{msg['role']}: {msg['content']}"
            for msg in self.messages
        )

    def clear(self) -> None:
        """Clear all messages from history."""
        self.messages.clear()
        self._current_chars = 0

# Alias for backward compatibility
HistoryManager = ChatHistoryManager