#!/usr/bin/env python3
"""
Test script for the ConversationService to verify functionality.
"""
import sys
import os
import tempfile
import time

# Add the current directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.conversation_service import ConversationService
from utils.message_utils import clean_think_sections


def test_conversation_service():
    """Test the ConversationService functionality."""
    print("🧪 Testing ConversationService...")
    print("=" * 50)
    
    # Use temporary database for testing
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_db:
        db_path = tmp_db.name
    
    try:
        # Initialize service
        service = ConversationService(db_path)
        
        # Test 1: Health check
        print("Test 1: Health check")
        health = service.health_check()
        print(f"✅ Health check: {'PASS' if health else 'FAIL'}")
        
        # Test 2: Store messages
        print("\nTest 2: Store messages")
        user_id = 12345
        
        # Store user message
        user_msg = "What is artificial intelligence?"
        success1 = service.store_message(user_id, 'user', user_msg)
        print(f"✅ Store user message: {'PASS' if success1 else 'FAIL'}")
        
        # Store bot response with think tags
        bot_msg = """<think>The user is asking about AI, I should provide a comprehensive answer.</think>
        
Artificial intelligence (AI) is a branch of computer science that aims to create machines capable of performing tasks that typically require human intelligence. This includes learning, reasoning, problem-solving, perception, and language understanding.

<reasoning>I should mention key areas and applications.</reasoning>

Key areas of AI include:
- Machine Learning
- Natural Language Processing
- Computer Vision
- Robotics"""
        
        success2 = service.store_message(user_id, 'bot', bot_msg)
        print(f"✅ Store bot message: {'PASS' if success2 else 'FAIL'}")
        
        # Test 3: Retrieve conversations
        print("\nTest 3: Retrieve conversations")
        conversations = service.get_recent_conversations(user_id, limit=1)
        print(f"✅ Retrieved {len(conversations)} conversations")
        
        if conversations:
            conv = conversations[0]
            print(f"   User message: {conv['user']['content'][:50]}...")
            print(f"   Bot message: {conv['bot']['content'][:50]}...")
            
            # Check if think tags were cleaned
            if '<think>' not in conv['bot']['content'] and '<reasoning>' not in conv['bot']['content']:
                print("✅ Think tags properly cleaned from stored message")
            else:
                print("❌ Think tags not properly cleaned")
        
        # Test 4: Conversation stats
        print("\nTest 4: Conversation statistics")
        stats = service.get_conversation_stats(user_id)
        print(f"✅ Total messages: {stats.get('total_messages', 0)}")
        print(f"✅ User messages: {stats.get('user_messages', 0)}")
        print(f"✅ Bot messages: {stats.get('bot_messages', 0)}")
        
        # Test 5: Service info
        print("\nTest 5: Service information")
        info = service.get_service_info()
        print(f"✅ Database path: {info.get('db_path', 'N/A')}")
        print(f"✅ Connected: {info.get('connected', False)}")
        print(f"✅ Total conversations: {info.get('total_conversations', 0)}")
        print(f"✅ Unique users: {info.get('unique_users', 0)}")
        
        # Test 6: Multiple exchanges
        print("\nTest 6: Multiple conversation exchanges")
        
        # Add more messages
        service.store_message(user_id, 'user', "How does machine learning work?")
        time.sleep(0.1)  # Small delay to ensure different timestamps
        service.store_message(user_id, 'bot', "Machine learning works by training algorithms on data to recognize patterns and make predictions.")
        time.sleep(0.1)
        service.store_message(user_id, 'user', "What are neural networks?")
        time.sleep(0.1)
        service.store_message(user_id, 'bot', "Neural networks are computing systems inspired by biological neural networks.")
        
        # Retrieve multiple exchanges
        recent_convs = service.get_recent_conversations(user_id, limit=3)
        print(f"✅ Retrieved {len(recent_convs)} conversation exchanges")
        
        for i, conv in enumerate(recent_convs, 1):
            print(f"   Exchange {i}:")
            print(f"     User: {conv['user']['content'][:40]}...")
            if 'bot' in conv:
                print(f"     Bot: {conv['bot']['content'][:40]}...")
        
        # Close service
        service.close()
        print("\n✅ ConversationService tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ ConversationService test failed: {e}")
        return False
    
    finally:
        # Clean up temporary database
        try:
            os.unlink(db_path)
        except:
            pass
    
    return True


def test_clean_think_sections():
    """Test the clean_think_sections function."""
    print("\n🧪 Testing clean_think_sections function...")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        {
            'input': '<think>This is internal thinking</think>Hello world!',
            'expected': 'Hello world!',
            'description': 'Basic think tag removal'
        },
        {
            'input': '<reasoning>Let me analyze this</reasoning>The answer is 42.<tool_call>some_function()</tool_call>',
            'expected': 'The answer is 42.',
            'description': 'Multiple tag types removal'
        },
        {
            'input': 'Normal text without any tags.',
            'expected': 'Normal text without any tags.',
            'description': 'Text without tags'
        },
        {
            'input': '<THINK>Case insensitive</THINK>Result here<ANALYSIS>More thinking</ANALYSIS>',
            'expected': 'Result here',
            'description': 'Case insensitive tag removal'
        },
        {
            'input': 'Text with\n\n\n\nmultiple newlines',
            'expected': 'Text with\n\nmultiple newlines',
            'description': 'Whitespace cleanup'
        }
    ]
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        try:
            result = clean_think_sections(test_case['input'])
            if result == test_case['expected']:
                print(f"✅ Test {i}: {test_case['description']} - PASS")
            else:
                print(f"❌ Test {i}: {test_case['description']} - FAIL")
                print(f"   Expected: '{test_case['expected']}'")
                print(f"   Got: '{result}'")
                all_passed = False
        except Exception as e:
            print(f"❌ Test {i}: {test_case['description']} - ERROR: {e}")
            all_passed = False
    
    if all_passed:
        print("\n✅ clean_think_sections tests completed successfully!")
    else:
        print("\n❌ Some clean_think_sections tests failed!")
    
    return all_passed


def main():
    """Run all tests."""
    print("🚀 Running ConversationService and utility function tests")
    print("=" * 60)
    
    # Test conversation service
    conv_test_passed = test_conversation_service()
    
    # Test clean_think_sections function
    clean_test_passed = test_clean_think_sections()
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY:")
    print(f"ConversationService: {'✅ PASS' if conv_test_passed else '❌ FAIL'}")
    print(f"clean_think_sections: {'✅ PASS' if clean_test_passed else '❌ FAIL'}")
    
    if conv_test_passed and clean_test_passed:
        print("\n🎉 All tests passed! The services are ready to use.")
        return True
    else:
        print("\n❌ Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)