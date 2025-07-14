import pytest
from cli_chatbot.chat.history import ChatHistoryManager

class TestChatHistoryManager:
    """Test suite for ChatHistoryManager functionality."""

    def test_add_message_storage(self):
        """Test that messages are stored correctly."""
        history = ChatHistoryManager(max_chars=1000)
        history.add_message("user", "Hello")
        history.add_message("assistant", "Hi there!")
        
        assert len(history.messages) == 2
        assert history.messages[0]["role"] == "user"
        assert history.messages[0]["content"] == "Hello"
        assert history.messages[1]["role"] == "assistant"
        assert history.messages[1]["content"] == "Hi there!"

    def test_history_rolling(self):
        """Test that older messages are removed when character limit is exceeded."""
        history = ChatHistoryManager(max_chars=20)
        history.add_message("user", "1234567890")  # 10 chars
        history.add_message("assistant", "1234567890")  # 10 chars (total 20)
        history.add_message("user", "X")  # Should remove first message
        
        assert len(history.messages) == 2
        assert history.messages[0]["content"] == "1234567890"  # assistant
        assert history.messages[1]["content"] == "X"  # new user

    def test_format_context(self):
        """Test history formatting into LLM context string."""
        history = ChatHistoryManager(max_chars=1000)
        history.add_message("user", "Hello")
        history.add_message("assistant", "Hi!")
        
        context = history.get_context_string()
        assert "user: Hello" in context
        assert "assistant: Hi!" in context
        assert context.count("\n") == 1  # One line break between messages

    def test_empty_history(self):
        """Test handling of empty history."""
        history = ChatHistoryManager(max_chars=1000)
        
        assert len(history.messages) == 0
        assert history.get_context_string() == ""

    def test_varying_message_lengths(self):
        """Test handling messages with different lengths."""
        history = ChatHistoryManager(max_chars=30)
        # Add messages that will eventually exceed limit
        history.add_message("user", "Short")  # 5
        history.add_message("assistant", "Medium length")  # 12 (total 17)
        history.add_message("user", "A very long message that exceeds")  # 31 chars
        
        # Last message should be truncated since it exceeds max_chars alone
        assert len(history.messages) == 1
        assert len(history.messages[0]["content"]) <= 30  # Should be truncated to max_chars