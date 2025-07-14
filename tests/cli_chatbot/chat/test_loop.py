import unittest
from unittest.mock import Mock, patch

from cli_chatbot.chat.history import HistoryManager
from cli_chatbot.llm.interface import LLMInterface

class TestChatLoop(unittest.TestCase):
    """Tests for the ChatLoop class."""

    def test_initialization(self):
        """Test ChatLoop initializes with history manager and LLM client."""
        mock_history = Mock(spec=HistoryManager)
        mock_llm = Mock(spec=LLMInterface)
        
        # This will fail until ChatLoop is implemented
        from cli_chatbot.chat.loop import ChatLoop
        chat_loop = ChatLoop(mock_history, mock_llm)
        
        self.assertEqual(chat_loop.history_manager, mock_history)
        self.assertEqual(chat_loop.llm_client, mock_llm)

    @patch('builtins.input', side_effect=['Hello', 'exit'])
    @patch('builtins.print')
    def test_handle_user_input(self, mock_print, mock_input):
        """Test handling user input and displaying responses."""
        mock_history = Mock(spec=HistoryManager)
        mock_llm = Mock(spec=LLMInterface)
        mock_llm.send_message.return_value = "Test response"
        
        from cli_chatbot.chat.loop import ChatLoop
        chat_loop = ChatLoop(mock_history, mock_llm)
        chat_loop.run()
        
        mock_print.assert_any_call("Assistant: Test response")
        mock_input.assert_called()
        mock_llm.send_message.assert_called()

    def test_messages_added_to_history(self):
        """Test messages are added to history manager."""
        mock_history = Mock(spec=HistoryManager)
        mock_llm = Mock(spec=LLMInterface)
        mock_llm.send_message.return_value = "Test response"
        
        from cli_chatbot.chat.loop import ChatLoop
        chat_loop = ChatLoop(mock_history, mock_llm)
        chat_loop.process_message("Test message")
        
        # Verify both user and assistant messages were added
        mock_history.add_message.assert_any_call("user", "Test message")
        mock_history.add_message.assert_any_call("assistant", "Test response")
        mock_history.add_message.assert_called_with("assistant", "Test response")
        mock_llm.send_message.assert_called()

    def test_history_context_passed_to_llm(self):
        """Test history context is passed to LLM."""
        mock_history = Mock(spec=HistoryManager)
        mock_history.get_context_string.return_value = "user: Test"
        mock_llm = Mock(spec=LLMInterface)
        
        from cli_chatbot.chat.loop import ChatLoop
        chat_loop = ChatLoop(mock_history, mock_llm)
        chat_loop.process_message("Test message")
        
        mock_llm.send_message.assert_called_with("user: Test")

    @patch('builtins.input', return_value='exit')
    @patch('builtins.print')
    def test_graceful_exit(self, mock_print, mock_input):
        """Test chat loop exits gracefully on exit command."""
        mock_history = Mock(spec=HistoryManager)
        mock_llm = Mock(spec=LLMInterface)
        
        from cli_chatbot.chat.loop import ChatLoop
        chat_loop = ChatLoop(mock_history, mock_llm)
        chat_loop.run()
        
        mock_print.assert_called_with("Exiting chat...")

if __name__ == '__main__':
    unittest.main()