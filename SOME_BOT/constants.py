import os

# Bot Configuration - Load from environment variables
OLLAMA_EMBEDDING_MODEL = os.getenv('OLLAMA_EMBEDDING_MODEL', "dengcao/Qwen3-Embedding-0.6B:Q8_0")
OLLAMA_RERANKER_MODEL = os.getenv('OLLAMA_RERANKER_MODEL', "dengcao/Qwen3-Reranker-4B:Q4_K_M")
OLLAMA_GENERATION_MODEL = os.getenv('OLLAMA_GENERATION_MODEL', "qwen3:4b")
QDRANT_COLLECTION_NAME = os.getenv('QDRANT_COLLECTION_NAME', "markdown_pages")

# RAG Configuration
VECTOR_SEARCH_LIMIT = 50  # Number of initial results from vector search
RERANKER_LIMIT = 10       # Number of results after reranking
MAX_MESSAGE_LENGTH = 4000 # Maximum Telegram message length

# New RAG Pipeline Configuration
TOP_EMBEDDER_RESULTS = int(os.getenv('TOP_EMBEDDER_RESULTS', "5"))  # Top results from embedder to guarantee in context
TOP_RERANKER_RESULTS = int(os.getenv('TOP_RERANKER_RESULTS', "5"))  # Top results from reranker to include
MAX_CONTEXT_CHARS = int(os.getenv('MAX_CONTEXT_CHARS', "20000"))    # Maximum context characters for LLM

# Two-Phase Context Assembly Configuration
TOP_CHUNKS_FOR_CONTEXT = int(os.getenv('TOP_CHUNKS_FOR_CONTEXT', "5"))  # Top chunks from vector search (Block 1)
TOP_COMPLETE_PAGES = int(os.getenv('TOP_COMPLETE_PAGES', "5"))           # Top complete pages after reranking (Block 2)

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Bot Messages - English
START_MESSAGE_EN = """🎯 **ITMO AI Programs Specialist Consultant**

Hello! I'm your **specialized consultant** exclusively for ITMO University's two Master's programs in Artificial Intelligence:

**🤖 "Artificial Intelligence" (Искусственный интеллект)**
→ Technical AI development, machine learning, neural networks, research

**📊 "AI Product Management" (Управление ИИ-продуктами)**
→ Business strategy, AI product development, team management, commercialization

**⚠️ IMPORTANT: I consult ONLY on these two AI programs!**

**What I can help you with:**
• Compare these two AI programs in detail
• Analyze your background to recommend the best AI program
• Explain career paths in technical AI vs AI product management
• Help choose courses and specializations within these programs
• Plan your academic journey in AI at ITMO

**Perfect questions for me:**
• "I'm a software engineer - which AI program fits better?"
• "What's the difference between technical AI and AI product management?"
• "Which AI program leads to better career opportunities?"
• "What prerequisites do I need for each AI program?"

**🚀 Ready to find your perfect AI program at ITMO?**
Tell me about your background, interests, and career goals in AI!"""

HELP_MESSAGE_EN = """**Available Commands:**
/start - Welcome message and introduction
/help - Show this help message
/history - View your recent conversation history

**🎯 My Specialization:**
I am a **specialized consultant** for exactly TWO Master's programs at ITMO:

• **🤖 "Artificial Intelligence"** - Technical AI development and research
• **📊 "AI Product Management"** - Business and management of AI products

**⚠️ I do NOT consult on other programs!**

If you ask about other programs, I'll politely redirect you to these two AI programs.

**How to get the best help:**
Tell me about your:
• Educational background
• Work experience
• Interest in technical vs business aspects of AI
• Career goals in AI field

I'll provide personalized recommendations between these two excellent AI programs!"""

ERROR_MESSAGE_EN = "❌ Sorry, I encountered an error processing your request about our AI programs. Please try again later."

NO_RELEVANT_CONTENT_MESSAGE_EN = """I couldn't find specific information to answer your question about our AI programs.

🎯 **Remember: I specialize exclusively in:**
• **"Artificial Intelligence"** - Technical AI program
• **"AI Product Management"** - AI business program

Please ask about these programs' curricula, requirements, career paths, or help choosing between them!"""

PROCESSING_MESSAGE_EN = "🔍 Analyzing your request and preparing recommendations..."

QDRANT_ERROR_MESSAGE_EN = "❌ Database is temporarily unavailable. Please try again later."

OLLAMA_ERROR_MESSAGE_EN = "❌ AI services are temporarily unavailable. Please try again later."

# Bot Messages - Russian
START_MESSAGE_RU = """🎯 **Специализированный консультант по программам ИИ ИТМО**

Привет! Я ваш **узкоспециализированный консультант** исключительно по двум магистерским программам ИТМО в области искусственного интеллекта:

**🤖 "Искусственный интеллект" (Artificial Intelligence)**
→ Техническая разработка ИИ, машинное обучение, нейросети, исследования

**📊 "Управление ИИ-продуктами" (AI Product Management)**
→ Бизнес-стратегия, разработка ИИ-продуктов, управление командами, коммерциализация

**⚠️ ВАЖНО: Я консультирую ТОЛЬКО по этим двум программам ИИ!**

**Чем могу помочь:**
• Детально сравнить эти две программы ИИ
• Проанализировать ваш бэкграунд для выбора лучшей программы ИИ
• Объяснить карьерные пути в техническом ИИ vs продуктовом управлении ИИ
• Помочь выбрать курсы и специализации в рамках этих программ
• Спланировать учебный путь в области ИИ в ИТМО

**Идеальные вопросы для меня:**
• "Я программист - какая программа ИИ подойдет лучше?"
• "В чем разница между техническим ИИ и управлением ИИ-продуктами?"
• "Какая программа ИИ дает лучшие карьерные возможности?"
• "Какие требования для поступления на каждую программу ИИ?"

**🚀 Готовы найти идеальную программу ИИ в ИТМО?**
Расскажите о своем бэкграунде, интересах и карьерных целях в области ИИ!"""

HELP_MESSAGE_RU = """**Доступные команды:**
/start - Приветственное сообщение и инструкция
/help - Показать это сообщение помощи
/history - Посмотреть историю ваших разговоров

**🎯 Моя специализация:**
Я **узкоспециализированный консультант** по двум конкретным магистерским программам ИТМО:

• **🤖 "Искусственный интеллект"** - Техническая разработка и исследования ИИ
• **📊 "Управление ИИ-продуктами"** - Бизнес и управление продуктами ИИ

**⚠️ Я НЕ консультирую по другим программам!**

Если спросите о других программах, я вежливо перенаправлю вас на эти две программы ИИ.

**Как получить лучшую помощь:**
Расскажите мне о своем:
• Образовательном бэкграунде
• Опыте работы
• Интересе к техническим vs бизнес-аспектам ИИ
• Карьерных целях в области ИИ

Я дам персональные рекомендации между этими двумя отличными программами ИИ!"""

ERROR_MESSAGE_RU = "❌ Извините, произошла ошибка при обработке вашего запроса о наших программах ИИ. Попробуйте позже."

NO_RELEVANT_CONTENT_MESSAGE_RU = """Я не смог найти конкретную информацию для ответа на ваш вопрос о наших программах ИИ.

🎯 **Помните: Я специализируюсь исключительно на:**
• **"Искусственный интеллект"** - Техническая программа ИИ
• **"Управление ИИ-продуктами"** - Бизнес-программа ИИ

Пожалуйста, спрашивайте об учебных планах, требованиях, карьерных путях этих программ или помощи в выборе между ними!"""

PROCESSING_MESSAGE_RU = "🔍 Анализирую ваш запрос и подбираю рекомендации..."

QDRANT_ERROR_MESSAGE_RU = "❌ База данных временно недоступна. Попробуйте позже."

OLLAMA_ERROR_MESSAGE_RU = "❌ ИИ сервисы временно недоступны. Попробуйте позже."

# Specialization Messages - English
OFF_TOPIC_REDIRECT_MESSAGE_EN = """🎯 I specialize exclusively in consulting on two AI Master's programs at ITMO:

• **🤖 "Artificial Intelligence"** - Technical AI development and research
• **📊 "AI Product Management"** - Business and AI product management

I don't provide information about other programs or topics.

**Let's focus on AI!** Tell me about your background and interests in artificial intelligence, and I'll help you choose the perfect AI program at ITMO! 🚀"""

AI_PROGRAM_FOCUS_MESSAGE_EN = """**🎯 My expertise is focused on these two excellent AI programs:**

**🤖 "Artificial Intelligence"**
→ Machine learning, neural networks, algorithms, AI research
→ Perfect for: Software engineers, researchers, technical specialists

**📊 "AI Product Management"**
→ AI product strategy, team management, business development
→ Perfect for: Business analysts, project managers, entrepreneurs

**Which aspect of AI interests you more - technical development or business management?**"""

# Specialization Messages - Russian
OFF_TOPIC_REDIRECT_MESSAGE_RU = """🎯 Я специализируюсь исключительно на консультировании по двум магистерским программам ИИ в ИТМО:

• **🤖 "Искусственный интеллект"** - Техническая разработка и исследования ИИ
• **📊 "Управление ИИ-продуктами"** - Бизнес и управление продуктами ИИ

Я не предоставляю информацию о других программах или темах.

**Давайте сосредоточимся на ИИ!** Расскажите о своем бэкграунде и интересах в области искусственного интеллекта, и я помогу выбрать идеальную программу ИИ в ИТМО! 🚀"""

AI_PROGRAM_FOCUS_MESSAGE_RU = """**🎯 Моя экспертиза сосредоточена на этих двух отличных программах ИИ:**

**🤖 "Искусственный интеллект"**
→ Машинное обучение, нейросети, алгоритмы, исследования ИИ
→ Идеально для: Программистов, исследователей, технических специалистов

**📊 "Управление ИИ-продуктами"**
→ Стратегия ИИ-продуктов, управление командами, бизнес-развитие
→ Идеально для: Бизнес-аналитиков, проект-менеджеров, предпринимателей

**Какой аспект ИИ вас больше интересует - техническая разработка или бизнес-управление?**"""

# Environment Variables
QDRANT_HOST = os.getenv('QDRANT_HOST', "qdrant")
QDRANT_PORT = int(os.getenv('QDRANT_PORT', "6333"))
OLLAMA_HOST = os.getenv('OLLAMA_HOST', "host.orb.internal")
OLLAMA_PORT = int(os.getenv('OLLAMA_PORT', "11434"))
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Message Templates by Language
MESSAGES = {
    'en': {
        'start': START_MESSAGE_EN,
        'help': HELP_MESSAGE_EN,
        'error': ERROR_MESSAGE_EN,
        'no_content': NO_RELEVANT_CONTENT_MESSAGE_EN,
        'processing': PROCESSING_MESSAGE_EN,
        'qdrant_error': QDRANT_ERROR_MESSAGE_EN,
        'ollama_error': OLLAMA_ERROR_MESSAGE_EN,
        'off_topic_redirect': OFF_TOPIC_REDIRECT_MESSAGE_EN,
        'ai_program_focus': AI_PROGRAM_FOCUS_MESSAGE_EN,
    },
    'ru': {
        'start': START_MESSAGE_RU,
        'help': HELP_MESSAGE_RU,
        'error': ERROR_MESSAGE_RU,
        'no_content': NO_RELEVANT_CONTENT_MESSAGE_RU,
        'processing': PROCESSING_MESSAGE_RU,
        'qdrant_error': QDRANT_ERROR_MESSAGE_RU,
        'ollama_error': OLLAMA_ERROR_MESSAGE_RU,
        'off_topic_redirect': OFF_TOPIC_REDIRECT_MESSAGE_RU,
        'ai_program_focus': AI_PROGRAM_FOCUS_MESSAGE_RU,
    }
}


def get_message(key: str, language: str = 'en') -> str:
    """
    Get localized message by key and language.
    
    Args:
        key: Message key
        language: Language code ('en' or 'ru')
        
    Returns:
        Localized message text
    """
    return MESSAGES.get(language, MESSAGES['en']).get(key, MESSAGES['en'][key])