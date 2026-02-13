import logging
import time
from pathlib import Path
from typing import Optional

from openai import OpenAI
from django.conf import settings

from apps.core.models import DadosNFSe
from apps.core.hybrid.models import DadosExtracao

logger = logging.getLogger(__name__)


class FocusedExtractor:
    """
    Extrator de dados focado - sem geracao de mensagem ao usuario.

    Usa prompt enxuto (~80 linhas vs 668 do prompt_conversacional.txt)
    e temperature baixa para maxima precisao na extracao.

    Retorna DadosExtracao (sem user_message), que e convertido
    para DadosNFSe para validacao Pydantic completa.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        prompt_path = Path(__file__).parent / 'prompts' / 'extraction.txt'
        self.SYSTEM_PROMPT = prompt_path.read_text(encoding='utf-8')

        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError(
                "API Key da OpenAI nao encontrada. "
                "Configure OPENAI_API_KEY no arquivo .env"
            )

        self.model = model
        self.client = OpenAI(api_key=self.api_key)

    def parse(
        self,
        user_message: str,
        dados_anterior: Optional[DadosNFSe] = None,
        conversation_history: Optional[list] = None,
    ) -> DadosNFSe:
        """
        Extrai dados da mensagem e retorna DadosNFSe validado.

        Args:
            user_message: Mensagem do usuario
            dados_anterior: Dados ja coletados na sessao (para contexto)
            conversation_history: Historico de mensagens da sessao

        Returns:
            DadosNFSe com dados extraidos e validados pelo Pydantic
        """
        logger.info(f"[hybrid] Extracao focada: {user_message[:80]}")

        context_text = dados_anterior.to_context() if dados_anterior else ""
        user_prompt = f"{context_text}\n\nMENSAGEM DO USUARIO:\n{user_message}" if context_text else user_message

        # Montar mensagens com historico (se disponivel)
        messages = self._build_messages(user_prompt, conversation_history)

        try:
            tempo_inicio = time.time()

            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=messages,
                response_format=DadosExtracao,
                max_tokens=512,
                temperature=0.1,
            )

            tempo_total = time.time() - tempo_inicio
            logger.info(f"[hybrid] Tempo OpenAI extracao: {tempo_total:.3f}s")

            if response.choices[0].message.refusal:
                logger.error(f"[hybrid] IA recusou: {response.choices[0].message.refusal}")
                return DadosNFSe()

            dados_extraidos = response.choices[0].message.parsed

            # Converter para DadosNFSe (validacao Pydantic completa)
            dados_nfse = dados_extraidos.to_dados_nfse()

            logger.info(
                f"[hybrid] Extracao OK. "
                f"cnpj={dados_nfse.cnpj.status}, "
                f"valor={dados_nfse.valor.status}, "
                f"descricao={dados_nfse.descricao.status}, "
                f"completo={dados_nfse.data_complete}"
            )

            return dados_nfse

        except Exception as e:
            logger.exception("[hybrid] Erro na extracao focada")
            return DadosNFSe()

    def _build_messages(self, user_prompt: str, conversation_history: Optional[list] = None) -> list:
        """
        Monta lista de mensagens para a API, incluindo historico.

        O historico ajuda a IA a entender contexto (ex: "o mesmo valor"
        se refere a um valor mencionado antes).
        """
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]

        # Adiciona historico (ultimas 4 mensagens user/assistant)
        if conversation_history:
            for msg in conversation_history[-4:]:
                if msg.get('role') in ('user', 'assistant'):
                    messages.append({
                        "role": msg['role'],
                        "content": msg['content']
                    })

        messages.append({"role": "user", "content": user_prompt})
        return messages
