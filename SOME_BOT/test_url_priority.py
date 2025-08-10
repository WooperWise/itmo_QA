#!/usr/bin/env python3
"""
Test script to verify URL priority scoring in reranker service.
This test ensures that target AI program URLs always get top scores.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.reranker_service import RerankerService
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_url_priority_scoring():
    """Test that target URLs get maximum scores and unwanted URLs get minimum scores."""
    
    print("=" * 80)
    print("CRITICAL URL PRIORITY TEST")
    print("=" * 80)
    
    # Initialize reranker service
    reranker = RerankerService()
    
    # Test cases with expected behavior
    test_cases = [
        {
            "url": "https://abit.itmo.ru/program/master/ai",
            "content": "Программа магистратуры Искусственный интеллект",
            "expected_score_range": (9.5, 10.0),
            "description": "Target AI program URL #1"
        },
        {
            "url": "https://abit.itmo.ru/program/master/ai_product", 
            "content": "Программа магистратуры Управление ИИ-продуктами",
            "expected_score_range": (9.5, 10.0),
            "description": "Target AI program URL #2"
        },
        {
            "url": "https://student.itmo.ru/ru/alfa",
            "content": "Альфа программа для студентов",
            "expected_score_range": (0.0, 3.0),
            "description": "Unwanted student URL"
        },
        {
            "url": "https://aspirantura.itmo.ru?main=4",
            "content": "Аспирантура ИТМО",
            "expected_score_range": (0.0, 3.0),
            "description": "Unwanted aspirantura URL"
        },
        {
            "url": "https://mega.itmo.ru/megaschool",
            "content": "Мегашкола ИТМО",
            "expected_score_range": (0.0, 3.0),
            "description": "Unwanted mega URL"
        },
        {
            "url": "https://start.itmo.ru",
            "content": "Стартовая страница ИТМО",
            "expected_score_range": (0.0, 3.0),
            "description": "Unwanted start URL"
        }
    ]
    
    # Test query about AI programs
    query = "программы искусственного интеллекта магистратура ИТМО"
    
    print(f"Testing query: '{query}'")
    print("-" * 80)
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['description']}")
        print(f"URL: {test_case['url']}")
        
        try:
            # Create reranking prompt
            prompt = reranker._create_reranking_prompt(
                query, 
                test_case['content'], 
                test_case['url']
            )
            
            # Get base score from LLM
            base_score = reranker._get_relevance_score(prompt)
            
            # Get URL boost
            url_boost = reranker._get_url_based_score_boost(test_case['url'])
            
            # Calculate final score
            final_score = base_score * url_boost
            final_score = max(0.0, min(10.0, final_score))  # Clamp to 0-10
            
            # Check if score is in expected range
            min_expected, max_expected = test_case['expected_score_range']
            is_correct = min_expected <= final_score <= max_expected
            
            status = "✅ PASS" if is_correct else "❌ FAIL"
            
            print(f"Base score: {base_score:.2f}")
            print(f"URL boost: {url_boost:.2f}")
            print(f"Final score: {final_score:.2f}")
            print(f"Expected range: {min_expected}-{max_expected}")
            print(f"Result: {status}")
            
            results.append({
                'test_case': test_case,
                'base_score': base_score,
                'url_boost': url_boost,
                'final_score': final_score,
                'is_correct': is_correct
            })
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append({
                'test_case': test_case,
                'error': str(e),
                'is_correct': False
            })
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r.get('is_correct', False))
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Target URLs will always rank highest.")
    else:
        print("⚠️  SOME TESTS FAILED! Reranker needs further tuning.")
        
        # Show failed tests
        print("\nFailed tests:")
        for r in results:
            if not r.get('is_correct', False):
                desc = r['test_case']['description']
                if 'error' in r:
                    print(f"- {desc}: ERROR - {r['error']}")
                else:
                    print(f"- {desc}: Score {r['final_score']:.2f} not in expected range {r['test_case']['expected_score_range']}")
    
    return results

def test_document_reranking():
    """Test full document reranking with mixed URLs."""
    
    print("\n" + "=" * 80)
    print("FULL DOCUMENT RERANKING TEST")
    print("=" * 80)
    
    reranker = RerankerService()
    
    # Create mock documents with different URLs
    documents = [
        {
            'payload': {
                'content': 'Альфа программа для студентов ИТМО',
                'url': 'https://student.itmo.ru/ru/alfa'
            },
            'score': 0.8
        },
        {
            'payload': {
                'content': 'Программа магистратуры Искусственный интеллект в ИТМО',
                'url': 'https://abit.itmo.ru/program/master/ai'
            },
            'score': 0.7
        },
        {
            'payload': {
                'content': 'Аспирантура в ИТМО',
                'url': 'https://aspirantura.itmo.ru?main=4'
            },
            'score': 0.9
        },
        {
            'payload': {
                'content': 'Программа магистратуры Управление ИИ-продуктами',
                'url': 'https://abit.itmo.ru/program/master/ai_product'
            },
            'score': 0.6
        },
        {
            'payload': {
                'content': 'Мегашкола ИТМО',
                'url': 'https://mega.itmo.ru/megaschool'
            },
            'score': 0.85
        }
    ]
    
    query = "программы искусственного интеллекта магистратура"
    
    print(f"Query: '{query}'")
    print(f"Input documents: {len(documents)}")
    
    # Rerank documents
    try:
        reranked = reranker.rerank_documents(query, documents, limit=5)
        
        print("\nReranking results:")
        print("-" * 50)
        
        for i, doc in enumerate(reranked, 1):
            url = doc.get('payload', {}).get('url', 'No URL')
            rerank_score = doc.get('rerank_score', 0.0)
            original_score = doc.get('original_score', 0.0)
            
            print(f"#{i}: rerank_score={rerank_score:.3f}, original_score={original_score:.3f}")
            print(f"     URL: {url}")
        
        # Check if target URLs are in top 2
        top_2_urls = [
            reranked[0].get('payload', {}).get('url', ''),
            reranked[1].get('payload', {}).get('url', '') if len(reranked) > 1 else ''
        ]
        
        target_urls = [
            'https://abit.itmo.ru/program/master/ai',
            'https://abit.itmo.ru/program/master/ai_product'
        ]
        
        target_in_top_2 = sum(1 for url in target_urls if any(target in top_url for top_url in top_2_urls))
        
        print(f"\nTarget URLs in top 2: {target_in_top_2}/2")
        
        if target_in_top_2 == 2:
            print("🎉 SUCCESS! Both target URLs are in top 2 positions.")
        else:
            print("⚠️  WARNING! Target URLs are not both in top 2 positions.")
            
        return reranked
        
    except Exception as e:
        print(f"❌ ERROR during reranking: {e}")
        return None

if __name__ == "__main__":
    print("Starting URL Priority Tests...")
    
    # Test individual URL scoring
    scoring_results = test_url_priority_scoring()
    
    # Test full document reranking
    reranking_results = test_document_reranking()
    
    print("\n" + "=" * 80)
    print("TESTS COMPLETED")
    print("=" * 80)