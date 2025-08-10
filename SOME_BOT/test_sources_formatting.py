#!/usr/bin/env python3
"""
Test script to verify sources formatting with the new changes.
"""
import sys
import os

# Add the botik directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.message_utils import format_sources

def test_sources_formatting():
    """Test the new sources formatting without deduplication."""
    
    # Sample sources data similar to what the RAG service returns
    test_sources = [
        {
            'page_info': 'Page 134',
            'url': 'http://e-maxx.ru/algo/topological_sort',
            'score': 0.832,
            'type': 'chunk'
        },
        {
            'page_info': 'Page 133',
            'url': 'http://e-maxx.ru/algo/strong_connected_components',
            'score': 0.622,
            'type': 'chunk'
        },
        {
            'page_info': 'Page 58',
            'url': 'http://e-maxx.ru/algo/generating_combinations',
            'score': 0.584,
            'type': 'chunk'
        },
        {
            'page_info': 'Page 104',
            'url': 'http://e-maxx.ru/algo/nearest_points',
            'score': 0.574,
            'type': 'chunk'
        },
        {
            'page_info': 'Page 139',
            'url': 'http://e-maxx.ru/algo/ternary_search',
            'score': 0.570,
            'type': 'chunk'
        },
        {
            'page_info': 'Page 133',
            'url': 'http://e-maxx.ru/algo/strong_connected_components',
            'score': 10.000,
            'type': 'page'
        },
        {
            'page_info': 'Page 134',
            'url': 'http://e-maxx.ru/algo/topological_sort',
            'score': 10.000,
            'type': 'page'
        },
        {
            'page_info': 'Page 13',
            'url': 'http://e-maxx.ru/algo/2_sat',
            'score': 10.000,
            'type': 'page'
        },
        {
            'page_info': 'Page 58',
            'url': 'http://e-maxx.ru/algo/generating_combinations',
            'score': 9.500,
            'type': 'page'
        },
        {
            'page_info': 'Page 104',
            'url': 'http://e-maxx.ru/algo/nearest_points',
            'score': 9.200,
            'type': 'page'
        }
    ]
    
    print("Testing sources formatting...")
    print("=" * 50)
    
    # Test Russian formatting
    print("Russian formatting:")
    ru_sources = format_sources(test_sources, 'ru')
    print(ru_sources)
    
    print("\n" + "=" * 50)
    
    # Test English formatting
    print("English formatting:")
    en_sources = format_sources(test_sources, 'en')
    print(en_sources)
    
    print("\n" + "=" * 50)
    print(f"Total sources displayed: {len(test_sources)}")
    print("✓ Test completed successfully!")

if __name__ == "__main__":
    test_sources_formatting()