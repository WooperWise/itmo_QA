"""
Deployment verification script for the QA Telegram Bot.
"""
import os
import sys
import subprocess
import time

def check_environment_variables():
    """Check if all required environment variables are set."""
    print("🔍 Checking Environment Variables...")
    
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'QDRANT_HOST',
        'QDRANT_PORT', 
        'OLLAMA_HOST',
        'OLLAMA_PORT',
        'QDRANT_COLLECTION_NAME'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    else:
        print("✅ All required environment variables are set")
        return True

def check_docker_network():
    """Check if the external network exists."""
    print("\n🌐 Checking Docker Network...")
    
    try:
        result = subprocess.run(
            ['docker', 'network', 'ls', '--filter', 'name=embeder_app-network'],
            capture_output=True, text=True
        )
        
        if 'embeder_app-network' in result.stdout:
            print("✅ Docker network 'embeder_app-network' exists")
            return True
        else:
            print("❌ Docker network 'embeder_app-network' not found")
            print("   Run: cd ../embeder && docker-compose up -d")
            return False
            
    except FileNotFoundError:
        print("❌ Docker not found. Please install Docker.")
        return False

def check_services_running():
    """Check if required services are running."""
    print("\n🔧 Checking Required Services...")
    
    services_ok = True
    
    # Check Qdrant
    try:
        result = subprocess.run(
            ['curl', '-s', 'http://localhost:6333/collections'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            print("✅ Qdrant is accessible")
        else:
            print("❌ Qdrant not accessible at localhost:6333")
            services_ok = False
    except:
        print("❌ Cannot check Qdrant (curl failed)")
        services_ok = False
    
    # Check Ollama
    try:
        result = subprocess.run(
            ['curl', '-s', 'http://localhost:11434/api/tags'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            print("✅ Ollama is accessible")
        else:
            print("❌ Ollama not accessible at localhost:11434")
            services_ok = False
    except:
        print("❌ Cannot check Ollama (curl failed)")
        services_ok = False
    
    return services_ok

def check_ollama_models():
    """Check if required Ollama models are available."""
    print("\n🤖 Checking Ollama Models...")
    
    required_models = [
        'dengcao/Qwen3-Embedding-0.6B:Q8_0',
        'dengcao/Qwen3-Reranker-0.6B:Q8_0',
        'qwen3:4b'
    ]
    
    try:
        result = subprocess.run(
            ['curl', '-s', 'http://localhost:11434/api/tags'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode != 0:
            print("❌ Cannot check models - Ollama not accessible")
            return False
        
        import json
        models_data = json.loads(result.stdout)
        available_models = [model['name'] for model in models_data.get('models', [])]
        
        missing_models = []
        for model in required_models:
            if model not in available_models:
                missing_models.append(model)
        
        if missing_models:
            print(f"❌ Missing models: {', '.join(missing_models)}")
            print("   Run: ./pull_models.sh")
            return False
        else:
            print("✅ All required models are available")
            return True
            
    except Exception as e:
        print(f"❌ Error checking models: {e}")
        return False

def check_qdrant_collection():
    """Check if the required Qdrant collection exists and has data."""
    print("\n📊 Checking Qdrant Collection...")
    
    try:
        # Check collections
        result = subprocess.run(
            ['curl', '-s', 'http://localhost:6333/collections'],
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode != 0:
            print("❌ Cannot check collection - Qdrant not accessible")
            return False
        
        import json
        collections_data = json.loads(result.stdout)
        collections = [col['name'] for col in collections_data.get('result', {}).get('collections', [])]
        
        if 'markdown_pages' not in collections:
            print("❌ Collection 'markdown_pages' not found")
            print("   Run the embedder to create and populate the collection")
            return False
        
        # Check collection info
        result = subprocess.run(
            ['curl', '-s', 'http://localhost:6333/collections/markdown_pages'],
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode == 0:
            collection_info = json.loads(result.stdout)
            points_count = collection_info.get('result', {}).get('points_count', 0)
            
            if points_count > 0:
                print(f"✅ Collection 'markdown_pages' exists with {points_count} points")
                return True
            else:
                print("❌ Collection 'markdown_pages' exists but is empty")
                print("   Run the embedder to populate the collection")
                return False
        else:
            print("❌ Cannot get collection info")
            return False
            
    except Exception as e:
        print(f"❌ Error checking collection: {e}")
        return False

def main():
    """Run all deployment checks."""
    print("🚀 QA Telegram Bot - Deployment Verification")
    print("=" * 50)
    
    checks = [
        ("Environment Variables", check_environment_variables),
        ("Docker Network", check_docker_network),
        ("Services Running", check_services_running),
        ("Ollama Models", check_ollama_models),
        ("Qdrant Collection", check_qdrant_collection),
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        try:
            if not check_func():
                all_passed = False
        except Exception as e:
            print(f"❌ {check_name} check failed: {e}")
            all_passed = False
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("🎉 All checks passed! Ready to deploy the bot.")
        print("\nTo deploy:")
        print("  docker-compose up -d")
        print("\nTo test:")
        print("  python test_rag.py")
    else:
        print("❌ Some checks failed. Please fix the issues above before deploying.")
        print("\nCommon fixes:")
        print("  1. Start services: cd ../embeder && docker-compose up -d")
        print("  2. Pull models: ./pull_models.sh")
        print("  3. Run embedder: cd ../embeder && docker-compose run embedder")
        print("  4. Set environment variables in .env file")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)