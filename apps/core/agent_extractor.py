import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, List
from openai import OpenAI
from django.conf import settings
from django.core.cache import cache

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
        prompt_file = 'extractor_system_reduzido.txt'
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
        """
        Extrai e valida dados de nota fiscal de uma mensagem
        
        Args:
            user_message: Mensagem do usuário contendo os dados da nota fiscal
            redis_state: Estado opcional do Redis com dados prévios da conversa
            
        Returns:
            Dict com dados extraídos e validados no formato especificado
        """
        logger.info("Iniciando extração de dados com AIExtractor")
        logger.info(f"Mensagem do usuário para extração: {user_message}")

        user_prompt = f"utilize primeiro esses dados para extrair e validar {user_message}"
        
        if redis_state:
                user_prompt += f" se tiver alguma informação de campo faltando, consultar como alternativa {json.dumps(redis_state, ensure_ascii=False)}"

        
        try:
            # Usando Structured Output da openai OBS: Versão Beta
            response = self.client.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=DadosNFSe,  # <- OpenAI garante a estrutura
                max_tokens=4096,
                temperature=0.1,
            )

            #verificar se a IA recusou responder
            if response.choices[0].message.refusal:
                logger.error(f"IA recusou processar: {response.choices[0].message.refusal}")
                return DadosNFSe(
                    user_message="Desculpe, não consegui processar sua solicitação. Tente Reformular."
                )
            
            # Extrai e retorn objeto Pydantic validado automaticamente
            dados = response.choices[0].message.parsed
            logger.info(f"Dados extraídos com sucesso, dados completos:{dados.data_complete}")     
            return dados
       
        except Exception as e:
            logger.exception("Erro ao chamar OpenAI Structured Outputs")
            return DadosNFSe(
            user_message=f"Erro ao processar sua mensagem. Tente novamente em instantes."
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