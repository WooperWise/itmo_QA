#!/usr/bin/env python3
"""
Test script for the educational consultant integration.
Tests the three-phase RAG pipeline with educational programs and conversation context.
"""

import sys
import os
import logging
from pathlib import Path

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.rag_service import RAGService
from services.conversation_service import ConversationService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_educational_programs_loading():
    """Test loading of educational programs data."""
    print("=" * 60)
    print("TEST 1: Educational Programs Loading")
    print("=" * 60)
    
    try:
        rag_service = RAGService()
        
        if rag_service.educational_programs_data:
            print(f"✅ Educational programs data loaded: {len(rag_service.educational_programs_data)} characters")
            print(f"Preview: {rag_service.educational_programs_data[:200]}...")
            return True
        else:
            print("❌ Educational programs data not loaded")
            return False
            
    except Exception as e:
        print(f"❌ Error loading educational programs: {e}")
        return False


def test_conversation_service():
    """Test conversation service functionality."""
    print("\n" + "=" * 60)
    print("TEST 2: Conversation Service")
    print("=" * 60)
    
    try:
        conv_service = ConversationService()
        
        # Test storing messages
        test_user_id = 12345
        
        # Store a test conversation
        conv_service.store_message(test_user_id, 'user', 'Какие программы по ИИ есть в ИТМО?')
        conv_service.store_message(test_user_id, 'bot', 'В ИТМО есть две магистерские программы по ИИ: "Искусственный интеллект" и "Управление ИИ-продуктами".')
        
        # Retrieve conversation
        conversations = conv_service.get_recent_conversations(test_user_id, limit=1)
        
        if conversations:
            print(f"✅ Conversation service working: {len(conversations)} exchanges retrieved")
            print(f"Sample exchange: {conversations[0]}")
            return True
        else:
            print("❌ No conversations retrieved")
            return False
            
    except Exception as e:
        print(f"❌ Error testing conversation service: {e}")
        return False


def test_health_checks():
    """Test health checks of all services."""
    print("\n" + "=" * 60)
    print("TEST 3: Service Health Checks")
    print("=" * 60)
    
    try:
        rag_service = RAGService()
        health_status = rag_service.health_check()
        
        print("Health Status:")
        for component, status in health_status.items():
            status_icon = "✅" if status else "❌"
            print(f"  {status_icon} {component}: {status}")
        
        return health_status.get('overall', False)
        
    except Exception as e:
        print(f"❌ Error checking health: {e}")
        return False


def test_three_phase_context():
    """Test the three-phase context creation."""
    print("\n" + "=" * 60)
    print("TEST 4: Three-Phase Context Creation")
    print("=" * 60)
    
    try:
        rag_service = RAGService()
        
        # Mock data for testing
        educational_data = rag_service.educational_programs_data or "Test educational data"
        conversation_context = [
            {
                'user': {'content': 'Какие дисциплины есть в программе ИИ?', 'timestamp': 1234567890},
                'bot': {'content': 'В программе ИИ есть множество дисциплин...', 'timestamp': 1234567891}
            }
        ]
        top_chunks = [
            {
                'payload': {
                    'content': 'Test chunk content about AI programs',
                    'page_info': 'Test Page',
                    'url': 'http://test.com'
                },
                'score': 0.95
            }
        ]
        complete_pages = [
            {
                'payload': {
                    'content': 'Complete page content about ITMO AI programs',
                    'page_info': 'ITMO AI Page',
                    'url': 'http://itmo.ru/ai'
                },
                'rerank_score': 0.88
            }
        ]
        
        # Test three-phase context creation
        context = rag_service.llm_service._create_three_phase_context(
            educational_data,
            conversation_context,
            top_chunks,
            complete_pages,
            max_context_chars=5000
        )
        
        if context:
            print(f"✅ Three-phase context created: {len(context)} characters")
            
            # Check if all blocks are present
            has_edu_block = "БЛОК 1: ОБРАЗОВАТЕЛЬНЫЕ ПРОГРАММЫ ИТМО" in context
            has_conv_block = "БЛОК 2: КОНТЕКСТ РАЗГОВОРА" in context
            has_rag_block = "БЛОК 3: РЕЛЕВАНТНАЯ ИНФОРМАЦИЯ ИЗ БАЗЫ ЗНАНИЙ" in context
            
            print(f"  Educational Programs Block: {'✅' if has_edu_block else '❌'}")
            print(f"  Conversation Context Block: {'✅' if has_conv_block else '❌'}")
            print(f"  RAG Results Block: {'✅' if has_rag_block else '❌'}")
            
            print(f"\nContext preview (first 300 chars):")
            print(context[:300] + "...")
            
            return has_edu_block and has_conv_block and has_rag_block
        else:
            print("❌ No context created")
            return False
            
    except Exception as e:
        print(f"❌ Error testing three-phase context: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Starting Educational Consultant Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Educational Programs Loading", test_educational_programs_loading),
        ("Conversation Service", test_conversation_service),
        ("Service Health Checks", test_health_checks),
        ("Three-Phase Context Creation", test_three_phase_context),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status_icon = "✅ PASS" if result else "❌ FAIL"
        print(f"{status_icon}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Educational consultant integration is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)