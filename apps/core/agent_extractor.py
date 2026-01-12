import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, List
from openai import OpenAI
from django.conf import settings
from django.core.cache import cache
import time 

from apps.core.models import DadosNFSe


logger = logging.getLogger(__name__)


class AIExtractor:
    """
    Extrai dados estruturados de mensagens usando OpenAI.

    Usa GPT-4o-mini para extrair informações de NFSe de mensagens
    em linguagem natural, com cache de 24h para reduzir custos.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Inicializa o extrator de dados de nota fiscal.
        
        Args:
            api_key: Chave da API OpenAI (se não fornecida, usa settings.OPENAI_API_KEY)
            model: Modelo OpenAI a ser usado (padrão: gpt-4o-mini)
        """

        # carregar prompt do arquivo
        #prompt_file = 'extractor_system_reduzido.txt'
        prompt_file = 'prompt_validacao_extracao.txt'
        prompt_path = Path(__file__).parent / 'prompts' / prompt_file
        self.SYSTEM_PROMPT = prompt_path.read_text(encoding='utf-8')

        # servico OpenAI
        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError(
                "API Key da OpenAI não encontrada. "
                "Configure OPENAI_API_KEY no arquivo .env ou passe via parâmetro."
            )
        
        self.model = model
        self.client = OpenAI(api_key=self.api_key)
    
    def parse(
        self, 
        user_message: str, 
        redis_state: Optional[Dict[str, Any]] = None
    ) -> DadosNFSe:

        logger.info("Iniciando extração de dados com AIExtractor")
        logger.info(f"Mensagem do usuário para extração: {user_message}")

        # Normaliza estado anterior (se existir)
        context_text = normalize_context(redis_state) if redis_state else ""


        if context_text:
            user_prompt = (
                f"{context_text}\n\n"
                f"MENSAGEM DO USUÁRIO:\n"
                f"{user_message}"
            )
        else:
            user_prompt = user_message

        logger.info(f"\n\nPrompt completo para extração:\n{user_prompt}\n\n")

        try:
            tempo_inicio = time.time()

            response = self.client.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=DadosNFSe,
                max_tokens=1024,
                temperature=0.4,
            )

            tempo_total = time.time() - tempo_inicio
            logger.info(
                f"\n\n⏱️ Tempo OpenAI: {tempo_total:.3f}s ({tempo_total*1000:.0f}ms)\n\n"
            )

            if response.choices[0].message.refusal:
                logger.error(f"IA recusou processar: {response.choices[0].message.refusal}")
                return DadosNFSe(
                    user_message="Desculpe, não consegui processar sua solicitação. Pode tentar reformular?"
                )

            dados = response.choices[0].message.parsed
            logger.info(f"Dados extraídos com sucesso. Completo: {dados.data_complete}")

            return dados

        except Exception as e:
            logger.exception("Erro ao chamar OpenAI Structured Outputs")
            return DadosNFSe(
                user_message="Erro ao processar sua mensagem. Tente novamente em instantes."
            )

    
    def parse_from_dict(self, data: Dict[str, Any]) -> DadosNFSe:
        """
        Processa dados no formato esperado pelo n8n
        
        Args:
            data: Dicionário contendo:
                - text: Mensagem do usuário
                - state: (opcional) Estado do Redis
                
        Returns:
            Dict com dados extraídos e validados
        """
        text = data.get("text", "")
        state = data.get("state")
        
        return self.parse(text, state)

def normalize_context(redis_state: Dict[str, Any]) -> str:
    """
    Normaliza o estado técnico (JSON) em um contexto textual neutro,
    adequado para ser enviado ao LLM sem induzir tom robótico.
    """
    if not redis_state:
        return ""

    lines = []

    cnpj = redis_state.get("cnpj", {})
    valor = redis_state.get("valor_formatted", {})
    descricao = redis_state.get("descricao", {})

    # CNPJ
    if cnpj.get("status") == "validated":
        lines.append("O CNPJ já foi informado.")
    else:
        lines.append("O CNPJ ainda não foi informado.")

    # Valor
    if valor.get("status") == "validated":
        lines.append("O valor do serviço já foi informado.")
    else:
        lines.append("O valor do serviço ainda não foi informado.")

    # Descrição
    if descricao.get("status") == "validated":
        lines.append("A descrição do serviço já foi informada.")
    elif descricao.get("status") == "warning":
        lines.append("A descrição do serviço ainda precisa ser confirmada.")
    else:
        lines.append("A descrição do serviço ainda não foi informada.")

    context_text = "CONTEXTO ATUAL:\n"
    for line in lines:
        context_text += f"- {line}\n"

    return context_text.strip()
