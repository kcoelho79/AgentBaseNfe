import logging
import time
from pathlib import Path
from typing import Optional, List

from openai import OpenAI
from django.conf import settings

from apps.core.models import Session

logger = logging.getLogger(__name__)


class ConversationalAI:
    """
    IA conversacional para responder perguntas dos usuarios.

    Usa knowledge_base.txt como fonte unica de conhecimento.
    Chamada APENAS quando o classificador detecta pergunta pura
    (sem dados para extrair).
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        prompts_dir = Path(__file__).parent / 'prompts'

        # Carregar knowledge base
        kb_path = prompts_dir / 'knowledge_base.txt'
        self.knowledge_base = kb_path.read_text(encoding='utf-8')

        # Carregar prompt conversacional e injetar knowledge base
        prompt_path = prompts_dir / 'conversational.txt'
        prompt_template = prompt_path.read_text(encoding='utf-8')
        self.SYSTEM_PROMPT = prompt_template.replace('{knowledge_base}', self.knowledge_base)

        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError(
                "API Key da OpenAI nao encontrada. "
                "Configure OPENAI_API_KEY no arquivo .env"
            )

        self.model = model
        self.client = OpenAI(api_key=self.api_key)

    def respond(
        self,
        pergunta: str,
        session: Optional[Session] = None,
    ) -> str:
        """
        Responde uma pergunta do usuario usando a knowledge base.

        Args:
            pergunta: Pergunta do usuario
            session: Sessao atual (para contexto de dados ja coletados)

        Returns:
            Resposta em texto natural
        """
        logger.info(f"[hybrid] Pergunta conversacional: {pergunta[:80]}")

        # Montar contexto da sessao
        contexto = ""
        if session and session.invoice_data:
            contexto = session.invoice_data.to_context()

        # Montar mensagens
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]

        # Historico recente (ultimas 4 mensagens)
        if session:
            for msg in session.get_conversation_history(limit=4):
                if msg.role in ('user', 'assistant'):
                    messages.append({"role": msg.role, "content": msg.content})

        # Adicionar contexto se houver dados parciais
        if contexto:
            user_content = f"{contexto}\n\nPERGUNTA DO USUARIO:\n{pergunta}"
        else:
            user_content = pergunta

        messages.append({"role": "user", "content": user_content})

        try:
            tempo_inicio = time.time()

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=256,
                temperature=0.7,
            )

            tempo_total = time.time() - tempo_inicio
            logger.info(f"[hybrid] Tempo OpenAI conversacional: {tempo_total:.3f}s")

            resposta = response.choices[0].message.content.strip()
            logger.info(f"[hybrid] Resposta conversacional: {resposta[:80]}")

            return resposta

        except Exception as e:
            logger.exception("[hybrid] Erro na IA conversacional")
            return "Desculpe, nao consegui processar sua pergunta. Pode tentar novamente?"
