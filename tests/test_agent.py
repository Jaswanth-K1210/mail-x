import unittest
import sys
import os
import json
from unittest.mock import patch, MagicMock

# Add parent directory to path to import email_agent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import email_agent

class TestEmailAgent(unittest.TestCase):

    def test_decide_strategy(self):
        """Test strategy selection logic."""
        self.assertEqual(
            email_agent.decide_strategy("Meeting Request"),
            "Propose a meeting time and ask for confirmation."
        )
        self.assertEqual(
            email_agent.decide_strategy("Support Query"),
            "Acknowledge the issue and promise support investigation."
        )
        self.assertEqual(
            email_agent.decide_strategy("Unknown Intent"),
            "Acknowledge receipt and ask how we can help."
        )

    @patch('email_agent.requests.post')
    def test_classify_intent_llm_success(self, mock_post):
        """Test intent classification with valid LLM response."""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": '{"intent": "Support Query", "confidence": 0.95}'
                }
            }]
        }
        mock_post.return_value = mock_response

        # Need to mock API KEY if not set
        with patch('email_agent.OPENROUTER_API_KEY', 'test_key'):
            result = email_agent.classify_intent_llm("Help me login")
            
        self.assertEqual(result['intent'], "Support Query")
        self.assertEqual(result['confidence'], 0.95)

    @patch('email_agent.requests.post')
    def test_classify_intent_llm_malformed_json(self, mock_post):
        """Test graceful failure on malformed JSON."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": 'This is not JSON'
                }
            }]
        }
        mock_post.return_value = mock_response

        with patch('email_agent.OPENROUTER_API_KEY', 'test_key'):
            # Should print warning (captured if needed) and return General
            result = email_agent.classify_intent_llm("junk text")
            
        self.assertEqual(result['intent'], "General")
        self.assertEqual(result['confidence'], 0.0)

    def test_save_to_memory(self):
        """Test that memory file is created and updated."""
        test_file = "test_memory.json"
        
        # Patch the MEMORY_FILE constant
        with patch('email_agent.MEMORY_FILE', test_file):
            if os.path.exists(test_file):
                os.remove(test_file)
            
            email_agent.save_to_memory(
                "test email",
                {"intent": "Test", "confidence": 1.0},
                "test reply"
            )
            
            self.assertTrue(os.path.exists(test_file))
            
            with open(test_file, 'r') as f:
                data = json.load(f)
                
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['email_text'], "test email")
            
            # Clean up
            os.remove(test_file)

if __name__ == '__main__':
    unittest.main()
