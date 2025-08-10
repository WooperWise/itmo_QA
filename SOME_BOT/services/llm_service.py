"""
LLM service using Ollama for generating answers based on retrieved context.
"""
import logging
import time
from typing import List, Dict, Any, Optional
import ollama
from constants import OLLAMA_HOST, OLLAMA_PORT, OLLAMA_GENERATION_MODEL
from utils.logging_utils import log_performance, log_error_with_context, log_generation_metrics

logger = logging.getLogger(__name__)


class LLMService:
    """Service for generating answers using Ollama LLM."""
    
    def __init__(self):
        """Initialize the LLM service."""
        self.client = None
        self.model = OLLAMA_GENERATION_MODEL
        self._connect()
    
    def _connect(self) -> None:
        """Connect to Ollama service."""
        try:
            host_url = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"
            self.client = ollama.Client(host=host_url)
            logger.info(f"Connected to Ollama LLM at {host_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Ollama LLM: {e}")
            self.client = None
    
    def _ensure_connection(self) -> bool:
        """Ensure connection to Ollama service."""
        if self.client is None:
            self._connect()
        return self.client is not None
    
    def _create_context_from_documents(self, documents: List[Dict[str, Any]],
                                     top_embedder_results: int = 5,
                                     top_reranker_results: int = 5,
                                     max_context_chars: int = 20000) -> str:
        """
        Create context string from retrieved documents with smart assembly logic.
        
        Args:
            documents: List of retrieved and reranked documents
            top_embedder_results: Number of top embedder results to guarantee in context
            top_reranker_results: Number of top reranker results to include
            max_context_chars: Maximum context characters for LLM
            
        Returns:
            Formatted context string within character limit
        """
        if not documents:
            return ""
        
        # First, add top embedder results (guaranteed inclusion)
        context_parts = []
        current_chars = 0
        
        # Add top embedder results first (but not more than we have)
        embedder_count = min(top_embedder_results, len(documents))
        for i in range(embedder_count):
            doc = documents[i]
            payload = doc.get('payload', {})
            content = payload.get('content', '')
            page_info = payload.get('page_info', f'Document {i+1}')
            url = payload.get('url', '')
            
            # Format each document with clear structure
            doc_text = f"=== ИСТОЧНИК {i+1}: {page_info} ===\nURL: {url}\nСОДЕРЖАНИЕ:\n{content}\n=== КОНЕЦ ИСТОЧНИКА {i+1} ==="
            
            # Check if adding this document would exceed the limit
            doc_chars = len(doc_text) + (3 if context_parts else 0)  # +3 for separator if needed
            if current_chars + doc_chars > max_context_chars:
                # Truncate this document to fit within the limit
                available_chars = max_context_chars - current_chars - 3
                if available_chars > 100:  # Only add if we have meaningful space
                    truncated_content = content[:available_chars - 100] + "... [truncated]"
                    doc_text = f"[Source {i+1}: {page_info}]\n{truncated_content}"
                    if url:
                        doc_text += f"\n[URL: {url}]"
                    context_parts.append(doc_text)
                break
            else:
                context_parts.append(doc_text)
                current_chars += doc_chars
        
        # Then add top reranker results (avoiding duplicates)
        reranker_added = 0
        for i in range(len(documents)):
            if reranker_added >= top_reranker_results:
                break
                
            doc = documents[i]
            payload = doc.get('payload', {})
            url = payload.get('url', '')
            
            # Check if this document is already included (by URL)
            already_included = False
            for part in context_parts:
                if url and url in part:
                    already_included = True
                    break
            
            if not already_included:
                content = payload.get('content', '')
                page_info = payload.get('page_info', f'Document {i+1}')
                
                # Format each document with metadata
                doc_text = f"[Source {len(context_parts)+1}: {page_info}]\n{content}"
                if url:
                    doc_text += f"\n[URL: {url}]"
                
                # Check if adding this document would exceed the limit
                doc_chars = len(doc_text) + (3 if context_parts else 0)  # +3 for separator if needed
                if current_chars + doc_chars > max_context_chars:
                    # Truncate this document to fit within the limit
                    available_chars = max_context_chars - current_chars - 3
                    if available_chars > 100:  # Only add if we have meaningful space
                        truncated_content = content[:available_chars - 100] + "... [truncated]"
                        doc_text = f"=== ИСТОЧНИК {len(context_parts)+1}: {page_info} ===\nURL: {url}\nСОДЕРЖАНИЕ:\n{truncated_content}\n=== КОНЕЦ ИСТОЧНИКА {len(context_parts)+1} ==="
                        context_parts.append(doc_text)
                    break
                else:
                    context_parts.append(doc_text)
                    current_chars += doc_chars
                    reranker_added += 1
        
        logger.info(f"Context assembled: {len(context_parts)} documents, {current_chars} chars (limit: {max_context_chars})")
        return "\n\n---\n\n".join(context_parts)
    
    def _create_three_phase_context(self, educational_programs_data: str,
                                   conversation_context: List[Dict[str, Any]],
                                   top_chunks: List[Dict[str, Any]],
                                   complete_pages: List[Dict[str, Any]],
                                   max_context_chars: int = 20000) -> str:
        """
        Create three-phase context with educational programs, conversation history, and RAG results.
        
        Args:
            educational_programs_data: Educational programs information from cool_diff.md
            conversation_context: Recent conversation exchanges
            top_chunks: Top chunks from vector search
            complete_pages: Complete pages after reranking
            max_context_chars: Maximum context characters for LLM
            
        Returns:
            Formatted three-phase context string
        """
        context_parts = []
        current_chars = 0
        
        # Block 1: Educational Programs (highest priority - always included)
        if educational_programs_data:
            block1_header = "=== БЛОК 1: ОБРАЗОВАТЕЛЬНЫЕ ПРОГРАММЫ ИТМО ==="
            context_parts.append(block1_header)
            current_chars += len(block1_header) + 4
            
            # Reserve 40% of context for educational programs
            edu_limit = int(max_context_chars * 0.4)
            if len(educational_programs_data) > edu_limit:
                truncated_edu = educational_programs_data[:edu_limit - 100] + "... [truncated]"
                context_parts.append(truncated_edu)
                current_chars += len(truncated_edu) + 4
            else:
                context_parts.append(educational_programs_data)
                current_chars += len(educational_programs_data) + 4
            
            logger.info(f"Added educational programs block: {len(educational_programs_data)} chars")
        
        # Block 2: Conversation Context (when available)
        if conversation_context:
            block2_header = "=== БЛОК 2: КОНТЕКСТ РАЗГОВОРА ==="
            context_parts.append(block2_header)
            current_chars += len(block2_header) + 4
            
            # Reserve 20% of context for conversation history
            conv_limit = int(max_context_chars * 0.2)
            conv_chars = 0
            
            for i, exchange in enumerate(conversation_context):
                if 'user' in exchange and 'bot' in exchange:
                    user_msg = exchange['user']['content']
                    bot_msg = exchange['bot']['content']
                    
                    exchange_text = f"ОБМЕН {i+1}:\nПользователь: {user_msg}\nБот: {bot_msg}"
                    
                    if conv_chars + len(exchange_text) + 4 > conv_limit:
                        break
                    
                    context_parts.append(exchange_text)
                    conv_chars += len(exchange_text) + 4
                    current_chars += len(exchange_text) + 4
            
            logger.info(f"Added conversation context: {len(conversation_context)} exchanges, {conv_chars} chars")
        
        # Block 3: RAG Results (remaining space)
        remaining_chars = max_context_chars - current_chars
        if remaining_chars > 500:  # Only add if we have meaningful space
            block3_header = "=== БЛОК 3: РЕЛЕВАНТНАЯ ИНФОРМАЦИЯ ИЗ БАЗЫ ЗНАНИЙ ==="
            context_parts.append(block3_header)
            current_chars += len(block3_header) + 4
            remaining_chars -= len(block3_header) + 4
            
            # Add top chunks (reserve 60% of remaining space)
            if top_chunks and remaining_chars > 200:
                chunks_limit = int(remaining_chars * 0.6)
                chunks_chars = 0
                
                for i, chunk in enumerate(top_chunks):
                    payload = chunk.get('payload', {})
                    content = payload.get('content', '')
                    page_info = payload.get('page_info', f'Chunk {i+1}')
                    url = payload.get('url', '')
                    score = chunk.get('score', 0)
                    
                    chunk_text = f"ЧАНК {i+1}: {page_info} (Score: {score:.3f})\nURL: {url}\n{content}"
                    
                    if chunks_chars + len(chunk_text) + 4 > chunks_limit:
                        # Try to truncate this chunk
                        available = chunks_limit - chunks_chars - 4
                        if available > 100:
                            truncated_content = content[:available - 100] + "... [truncated]"
                            chunk_text = f"ЧАНК {i+1}: {page_info} (Score: {score:.3f})\nURL: {url}\n{truncated_content}"
                            context_parts.append(chunk_text)
                            chunks_chars += len(chunk_text) + 4
                        break
                    else:
                        context_parts.append(chunk_text)
                        chunks_chars += len(chunk_text) + 4
                
                current_chars += chunks_chars
                remaining_chars -= chunks_chars
            
            # Add complete pages (remaining space)
            if complete_pages and remaining_chars > 200:
                for i, page in enumerate(complete_pages):
                    payload = page.get('payload', {})
                    content = payload.get('content', '')
                    page_info = payload.get('page_info', f'Page {i+1}')
                    url = payload.get('url', '')
                    score = page.get('rerank_score', page.get('score', 0))
                    
                    page_text = f"СТРАНИЦА {i+1}: {page_info} (Rerank Score: {score:.3f})\nURL: {url}\n{content}"
                    
                    if len(page_text) + 4 > remaining_chars:
                        # Try to truncate this page
                        if remaining_chars > 200:
                            truncated_content = content[:remaining_chars - 200] + "... [truncated]"
                            page_text = f"СТРАНИЦА {i+1}: {page_info} (Rerank Score: {score:.3f})\nURL: {url}\n{truncated_content}"
                            context_parts.append(page_text)
                            current_chars += len(page_text) + 4
                        break
                    else:
                        context_parts.append(page_text)
                        current_chars += len(page_text) + 4
                        remaining_chars -= len(page_text) + 4
        
        logger.info(f"Three-phase context assembled: edu_programs + {len(conversation_context)} conversations + {len(top_chunks)} chunks + {len(complete_pages)} pages, {current_chars} chars (limit: {max_context_chars})")
        return "\n\n".join(context_parts)
    
    def _create_system_prompt(self, language: str) -> str:
        """
        Create system prompt for educational consultant role based on language.
        
        Args:
            language: Response language ('en' or 'ru')
            
        Returns:
            System prompt text for educational consultant
        """
        if language == 'ru':
            return """КРИТИЧЕСКИ ВАЖНО: Ты консультант ТОЛЬКО по двум программам ИИ в ИТМО. ЗАПРЕЩЕНО упоминать любые другие программы!

🎯 ТВОЯ ЕДИНСТВЕННАЯ СПЕЦИАЛИЗАЦИЯ:
1. "Искусственный интеллект" (Artificial Intelligence) - техническая программа ИИ
2. "Управление ИИ-продуктами" (AI Product Management) - продуктовая программа ИИ

⚠️ СТРОГИЕ ПРАВИЛА:
- Ты консультант ТОЛЬКО по двум программам ИИ в ИТМО
- ЗАПРЕЩЕНО упоминать любые другие программы
- ВСЕГДА выбирай одну из двух программ ИИ
- НЕ используй секции <think> или <reasoning>

ДВЕ ПРОГРАММЫ:
1. "Искусственный интеллект" - для технических специалистов, программистов, исследователей
2. "Управление ИИ-продуктами" - для менеджеров, людей любящих общение, бизнес-ориентированных

КРИТЕРИИ ВЫБОРА:
- Общение с людьми → "Управление ИИ-продуктами"
- Программирование/алгоритмы → "Искусственный интеллект"
- Бизнес/менеджмент → "Управление ИИ-продуктами"
- Исследования/наука → "Искусственный интеллект"

СТРУКТУРА КОНТЕКСТА:
=== БЛОК 1: ОБРАЗОВАТЕЛЬНЫЕ ПРОГРАММЫ ИТМО ===
[Данные об учебных планах, дисциплинах, специализациях ТОЛЬКО по двум целевым программам ИИ]

=== БЛОК 2: КОНТЕКСТ РАЗГОВОРА ===
[История предыдущих вопросов и ответов с пользователем]

=== БЛОК 3: РЕЛЕВАНТНАЯ ИНФОРМАЦИЯ ИЗ БАЗЫ ЗНАНИЙ ===
[Дополнительная информация из документов о программах ИИ]

ПРАВИЛА КОНСУЛЬТИРОВАНИЯ:
1. ОБЯЗАТЕЛЬНО ВНИМАТЕЛЬНО ПРОЧИТАЙ ВСЕ ТРИ БЛОКА КОНТЕКСТА ПОЛНОСТЬЮ
2. ПРИОРИТИЗИРУЙ информацию из Блока 1 о двух целевых программах ИИ
3. ИСПОЛЬЗУЙ контекст разговора из Блока 2 для персонализации ответов
4. ДОПОЛНЯЙ ответы информацией из Блока 3 только о программах ИИ
5. Отвечай ТОЛЬКО на основе предоставленного контекста о программах ИИ
6. При отсутствии информации о программах ИИ - честно скажи об этом
7. Давай конкретные рекомендации по выбору между двумя программами ИИ
8. Учитывай бэкграунд студента для выбора между техническим и продуктовым направлением ИИ

ОБРАБОТКА НЕЦЕЛЕВЫХ ВОПРОСОВ:
Если спрашивают о других программах, отвечай: "Я специализируюсь исключительно на консультировании по двум программам ИИ в ИТМО: 'Искусственный интеллект' и 'Управление ИИ-продуктами'. Расскажите о своих интересах в области ИИ, и я помогу выбрать подходящую программу!"

СТИЛЬ ОБЩЕНИЯ:
- Дружелюбный и профессиональный тон
- Фокус на сравнении двух программ ИИ
- Персонализированные рекомендации между техническим и продуктовым направлением
- Мотивация к изучению ИИ в ИТМО

Помогай выбрать оптимальную программу ИИ в ИТМО на основе бэкграунда и целей студента."""
        else:
            return """CRITICALLY IMPORTANT: You are a consultant ONLY for two AI programs at ITMO. FORBIDDEN to mention any other programs!

🎯 YOUR ONLY SPECIALIZATION:
1. "Artificial Intelligence" (Искусственный интеллект) - technical AI program
2. "AI Product Management" (Управление ИИ-продуктами) - AI product program

⚠️ STRICT RULES:
- You are a consultant ONLY for two AI programs at ITMO
- FORBIDDEN to mention any other programs
- ALWAYS choose one of the two AI programs
- DO NOT use <think> or <reasoning> sections

TWO PROGRAMS:
1. "Artificial Intelligence" - for technical specialists, programmers, researchers
2. "AI Product Management" - for managers, people who love communication, business-oriented

SELECTION CRITERIA:
- Communication with people → "AI Product Management"
- Programming/algorithms → "Artificial Intelligence"
- Business/management → "AI Product Management"
- Research/science → "Artificial Intelligence"

CONTEXT STRUCTURE:
=== BLOCK 1: ITMO EDUCATIONAL PROGRAMS ===
[Data about curricula, courses, specializations ONLY for the two target AI programs]

=== BLOCK 2: CONVERSATION CONTEXT ===
[History of previous questions and answers with the user]

=== BLOCK 3: RELEVANT INFORMATION FROM KNOWLEDGE BASE ===
[Additional information from documents about AI programs]

CONSULTING RULES:
1. YOU MUST CAREFULLY READ ALL THREE CONTEXT BLOCKS COMPLETELY
2. PRIORITIZE information from Block 1 about the two target AI programs
3. USE conversation context from Block 2 to personalize responses
4. SUPPLEMENT answers with information from Block 3 only about AI programs
5. Answer ONLY based on provided context about AI programs
6. If information about AI programs is missing, honestly say so
7. Give specific recommendations for choosing between the two AI programs
8. Consider student's background for choosing between technical and product AI directions

HANDLING OFF-TOPIC QUESTIONS:
If asked about other programs, respond: "I specialize exclusively in consulting on two AI programs at ITMO: 'Artificial Intelligence' and 'AI Product Management'. Tell me about your interests in AI, and I'll help you choose the right program!"

COMMUNICATION STYLE:
- Friendly and professional tone
- Focus on comparing the two AI programs
- Personalized recommendations between technical and product directions
- Motivation for studying AI at ITMO

Help choose the optimal AI program at ITMO based on student's background and goals."""
    
    def _create_user_prompt(self, query: str, context: str, language: str) -> str:
        """
        Create user prompt with query and context.
        
        Args:
            query: User's question
            context: Retrieved context from documents
            language: Response language
            
        Returns:
            Formatted user prompt
        """
        if language == 'ru':
            return f"""Контекст из сайта:
{context}

Вопрос пользователя: {query}

Ответь на вопрос, используя только информацию из предоставленного контекста."""
        else:
            return f"""Context from website:
{context}

User question: {query}

Answer the question using only the information from the provided context."""
    
    @log_performance
    def generate_answer(self, query: str, documents: List[Dict[str, Any]],
                       language: str = 'en', max_retries: int = 2,
                       top_embedder_results: int = 5, top_reranker_results: int = 5,
                       max_context_chars: int = 20000) -> Optional[str]:
        """
        Generate answer based on query and retrieved documents.
        
        Args:
            query: User's question
            documents: List of retrieved and reranked documents
            language: Response language ('en' or 'ru')
            max_retries: Maximum number of retry attempts
            top_embedder_results: Number of top embedder results to guarantee in context
            top_reranker_results: Number of top reranker results to include
            max_context_chars: Maximum context characters for LLM
            
        Returns:
            Generated answer or None if failed
        """
        if not self._ensure_connection():
            logger.error("Cannot generate answer: no connection to Ollama")
            return None
        
        if not documents:
            logger.warning("No documents provided for answer generation")
            return None
        
        # Create context from documents with smart assembly
        context = self._create_context_from_documents(documents, top_embedder_results, top_reranker_results, max_context_chars)
        if not context:
            logger.warning("No valid context extracted from documents")
            return None
        
        # Create prompts
        system_prompt = self._create_system_prompt(language)
        user_prompt = self._create_user_prompt(query, context, language)
        
        logger.info(f"Generating answer for query: '{query[:50]}...' in {language}")
        logger.debug(f"Context length: {len(context)} chars, Documents: {len(documents)}")
        
        # Log first 500 characters of context for debugging
        context_preview = context[:500].replace('\n', '\\n')
        logger.debug(f"Context preview (first 500 chars): {context_preview}...")
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                response = self.client.generate(
                    model=self.model,
                    prompt=user_prompt,
                    system=system_prompt,
                    options={
                        'temperature': 0.3,  # Low temperature for factual responses
                        'top_p': 0.9,
                        'num_predict': 8192,  # Allow longer responses
                    }
                )
                
                duration = time.time() - start_time
                answer = response.get('response', '').strip()
                
                if answer:
                    # Log generation metrics
                    log_generation_metrics(answer, len(context), duration, language)
                    
                    logger.info(f"Generated answer of {len(answer)} chars in {duration:.2f}s")
                    return answer
                else:
                    logger.warning(f"Empty response from LLM on attempt {attempt + 1}")
                    
            except Exception as e:
                duration = time.time() - start_time if 'start_time' in locals() else 0
                logger.warning(f"Answer generation attempt {attempt + 1} failed after {duration:.2f}s: {e}")
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    log_error_with_context(
                        e,
                        {
                            'query_length': len(query),
                            'context_length': len(context),
                            'documents_count': len(documents),
                            'language': language,
                            'attempt': attempt + 1
                        }
                    )
        
        logger.error(f"Failed to generate answer after {max_retries} attempts")
        return None
    
    @log_performance
    def generate_answer_two_phase(self, query: str, top_chunks: List[Dict[str, Any]],
                                complete_pages: List[Dict[str, Any]], language: str = 'en',
                                max_retries: int = 2, max_context_chars: int = 20000,
                                conversation_context: List[Dict[str, Any]] = None,
                                educational_programs_data: str = None) -> Optional[str]:
        """
        Generate answer using three-phase context assembly with educational programs and conversation context.
        
        Args:
            query: User's question
            top_chunks: Top chunks from vector search
            complete_pages: Complete pages after reranking
            language: Response language ('en' or 'ru')
            max_retries: Maximum number of retry attempts
            max_context_chars: Maximum context characters for LLM
            conversation_context: Recent conversation exchanges
            educational_programs_data: Educational programs information
            
        Returns:
            Generated answer or None if failed
        """
        if not self._ensure_connection():
            logger.error("Cannot generate answer: no connection to Ollama")
            return None
        
        # Check if we have any context to work with
        if not top_chunks and not complete_pages and not educational_programs_data:
            logger.warning("No context provided for answer generation")
            return None
        
        # Create three-phase context
        context = self._create_three_phase_context(
            educational_programs_data or "",
            conversation_context or [],
            top_chunks,
            complete_pages,
            max_context_chars
        )
        
        if not context:
            logger.warning("No valid context extracted")
            return None
        
        # Create prompts
        system_prompt = self._create_system_prompt(language)
        user_prompt = self._create_user_prompt(query, context, language)
        
        logger.info(f"Generating three-phase answer for query: '{query[:50]}...' in {language}")
        logger.debug(f"Context length: {len(context)} chars, Educational: {bool(educational_programs_data)}, Conversations: {len(conversation_context or [])}, Chunks: {len(top_chunks)}, Pages: {len(complete_pages)}")
        
        # Log first 500 characters of context for debugging
        context_preview = context[:500].replace('\n', '\\n')
        logger.debug(f"Three-phase context preview (first 500 chars): {context_preview}...")
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                response = self.client.generate(
                    model=self.model,
                    prompt=user_prompt,
                    system=system_prompt,
                    options={
                        'temperature': 0.3,  # Low temperature for factual responses
                        'top_p': 0.9,
                        'num_predict': 8192,  # Allow longer responses
                    }
                )
                
                duration = time.time() - start_time
                answer = response.get('response', '').strip()
                
                if answer:
                    # Log generation metrics
                    log_generation_metrics(answer, len(context), duration, language)
                    
                    logger.info(f"Generated three-phase answer of {len(answer)} chars in {duration:.2f}s")
                    return answer
                else:
                    logger.warning(f"Empty response from LLM on attempt {attempt + 1}")
                    
            except Exception as e:
                duration = time.time() - start_time if 'start_time' in locals() else 0
                logger.warning(f"Three-phase answer generation attempt {attempt + 1} failed after {duration:.2f}s: {e}")
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    log_error_with_context(
                        e,
                        {
                            'query_length': len(query),
                            'context_length': len(context),
                            'educational_programs': bool(educational_programs_data),
                            'conversation_exchanges': len(conversation_context or []),
                            'chunks_count': len(top_chunks),
                            'pages_count': len(complete_pages),
                            'language': language,
                            'attempt': attempt + 1
                        }
                    )
        
        logger.error(f"Failed to generate three-phase answer after {max_retries} attempts")
        return None
    
    def generate_fallback_response(self, language: str = 'en') -> str:
        """
        Generate fallback response when no relevant content is found.
        
        Args:
            language: Response language
            
        Returns:
            Fallback response text
        """
        if language == 'ru':
            return ("Извините, я не смог найти релевантную информацию для ответа на ваш вопрос. "
                   "Я специализируюсь исключительно на консультировании по двум магистерским программам ИТМО:\n\n"
                   "🤖 **'Искусственный интеллект'** - техническая разработка и исследования ИИ\n"
                   "📊 **'Управление ИИ-продуктами'** - бизнес и управление продуктами ИИ\n\n"
                   "Расскажите о своих интересах в области ИИ, и я помогу выбрать подходящую программу!")
        else:
            return ("I couldn't find relevant information to answer your question. "
                   "I specialize exclusively in consulting on two ITMO master's programs:\n\n"
                   "🤖 **'Artificial Intelligence'** - technical AI development and research\n"
                   "📊 **'AI Product Management'** - business and AI product management\n\n"
                   "Tell me about your interests in AI, and I'll help you choose the right program!")
    
    def health_check(self) -> bool:
        """
        Check if the LLM service is healthy.
        
        Returns:
            True if service is healthy, False otherwise
        """
        try:
            if not self._ensure_connection():
                return False
            
            # Test with a simple generation
            test_response = self.client.generate(
                model=self.model,
                prompt="Test prompt",
                options={'num_predict': 10}
            )
            
            return bool(test_response.get('response'))
            
        except Exception as e:
            logger.error(f"LLM health check failed: {e}")
            return False
    
    def get_model_info(self) -> dict:
        """
        Get information about the current LLM model.
        
        Returns:
            Dictionary with model information
        """
        return {
            'model': self.model,
            'host': f"{OLLAMA_HOST}:{OLLAMA_PORT}",
            'healthy': self.health_check()
        }