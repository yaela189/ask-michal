# -*- coding: utf-8 -*-
import anthropic

from server.config import Settings
from server.ai.prompts import SYSTEM_PROMPT, REFUSAL_NO_KNOWLEDGE
from server.rag.retriever import KnowledgeRetriever
from server.security.filters import InputFilter, OutputFilter


class MichalEngine:
    def __init__(self, settings: Settings, retriever: KnowledgeRetriever):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model
        self.retriever = retriever
        self.input_filter = InputFilter()
        self.output_filter = OutputFilter()
        self.min_relevance_score = 0.3  # Minimum cosine similarity for FAISS IP

    def ask(self, question: str, conversation_history: list[dict] | None = None) -> dict:
        """Process a question through the full RAG + security pipeline."""

        # Step 1: Input security filter
        filter_result = self.input_filter.check(question)
        if filter_result.blocked:
            return {
                "answer": filter_result.refusal_message,
                "sources": [],
                "tokens_used": 0,
            }

        # Step 2: Retrieve relevant context
        retrieved = self.retriever.retrieve(question)

        # Step 3: Check if we found relevant context
        if not retrieved or all(r["score"] < self.min_relevance_score for r in retrieved):
            return {
                "answer": REFUSAL_NO_KNOWLEDGE,
                "sources": [],
                "tokens_used": 0,
            }

        # Step 4: Build prompt with context
        context = self.retriever.format_context(retrieved)
        system_prompt = SYSTEM_PROMPT.replace("{context}", context)

        # Step 5: Build messages (include recent conversation history)
        messages = []
        if conversation_history:
            for msg in conversation_history[-6:]:  # Last 3 exchanges
                messages.append(msg)
        messages.append({"role": "user", "content": question})

        # Step 6: Call Claude API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system_prompt,
            messages=messages,
        )

        answer_text = response.content[0].text
        tokens_used = response.usage.input_tokens + response.usage.output_tokens

        # Step 7: Output security filter
        answer_text = self.output_filter.sanitize(answer_text)

        # Step 8: Extract source references
        sources = list(
            dict.fromkeys(
                f"{r['source']} (עמוד {r['page']})" for r in retrieved
            )
        )

        return {
            "answer": answer_text,
            "sources": sources,
            "tokens_used": tokens_used,
        }
