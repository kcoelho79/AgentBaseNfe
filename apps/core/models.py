from django.db import models

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal, List
from decimal import Decimal
from datetime import datetime
from uuid import uuid4

import logging

from apps.core.states import SessionState, is_valid_transition

logger = logging.getLogger(__name__)

""" modelos Pydantic para dados extraidos pela IA Extractor
"""
class CampoExtraido(BaseModel):
    """ Base para campos estraidos pela IA """
    status: Literal['validated', 'null', 'error', 'warning'] = 'null'
    

class CNPJExtraido(CampoExtraido):
    cnpj_extracted: Optional[str] = None
    cnpj: Optional[str] = None
    cnpj_issue: Optional[str] = None
    error_type: Optional[str] = None
    razao_social: Optional[str] = None
    status : Literal['validated', 'null', 'error', 'warning'] = 'null'  

    @staticmethod
    def _validar_digitos_verificadores(cnpj: str) -> bool:
        """Valida dígitos verificadores do CNPJ."""
        if len(cnpj) != 14:
            return False
        
        # Primeiro dígito
        mult_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma_1 = sum(int(cnpj[i]) * mult_1[i] for i in range(12))
        dig_1 = 0 if (soma_1 % 11) < 2 else 11 - (soma_1 % 11)
        
        # Segundo dígito
        mult_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        soma_2 = sum(int(cnpj[i]) * mult_2[i] for i in range(13))
        dig_2 = 0 if (soma_2 % 11) < 2 else 11 - (soma_2 % 11)
        
        return cnpj[-2:] == f"{dig_1}{dig_2}"

    @model_validator(mode='after')
    def validar_cnpj_completo(self):
        """Validação rigorosa de CNPJ - BLOQUEIA dados inválidos."""
        # Se não tem CNPJ, não valida
        if not self.cnpj_extracted:
            return self
        
        cnpj_numeros = ''.join(filter(str.isdigit, self.cnpj_extracted))
        
        # Valida tamanho
        if len(cnpj_numeros) != 14:
            logger.error(f"CNPJ com tamanho inválido: {len(cnpj_numeros)} dígitos")
            self.status = 'error'
            self.error_type = 'FORMATO_INVALIDO'
            self.cnpj_issue = f'CNPJ deve ter 14 dígitos (informado: {len(cnpj_numeros)})'
            self.cnpj = None
            return self
        
        # Valida dígitos repetidos
        if cnpj_numeros == cnpj_numeros[0] * 14:
            logger.error(f"CNPJ com dígitos repetidos: {cnpj_numeros}")
            self.status = 'error'
            self.error_type = 'FORMATO_INVALIDO'
            self.cnpj_issue = 'CNPJ não pode ter todos os dígitos iguais'
            self.cnpj = None
            return self
        
        # Valida dígitos verificadores
        if not self._validar_digitos_verificadores(cnpj_numeros):
            logger.error(f"Dígitos verificadores inválidos: {cnpj_numeros}")
            self.status = 'error'
            self.error_type = 'DIGITO_VERIFICADOR_INVALIDO'
            self.cnpj_issue = 'Dígitos verificadores do CNPJ estão incorretos'
            self.cnpj = None
            return self
        
        
        # Se passou por todas as validações, mantém como validated
        self.status = 'validated'
        self.cnpj = cnpj_numeros
        self.cnpj_issue = None
        self.error_type = None
    
        logger.info(f"CNPJ validado com sucesso: {cnpj_numeros}")
        return self
    
    def consultar_receita(self, timeout: int = 5) -> bool:
        """Consulta dados na Receita (chamar após validação)."""
        if not self.cnpj or len(self.cnpj) != 14:
            return False
        
        try:
            import httpx
            response = httpx.get(
                f'https://brasilapi.com.br/api/cnpj/v1/{self.cnpj}',
                timeout=timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                self.razao_social = data.get('razao_social')
                logger.info(f"Razão Social: {self.razao_social}")
                return True
            return False
        except Exception as e:
            logger.warning(f"Erro ao consultar CNPJ: {e}")
            return False

class ValorExtraido(CampoExtraido):
    valor_extracted: Optional[str] = None
    valor: Optional[Decimal] = None
    valor_formatted: Optional[str] = None
    valor_issue: Optional[str] = None
    error_type: Optional[str] = None
    status : Literal['validated', 'null', 'error', 'warning'] = 'null'  

    @model_validator(mode='after')
    def validar_valor_completo(self):
        """Validação rigorosa de Valor - BLOQUEIA dados inválidos."""
        # Se não tem valor ou já está em erro, não valida
        if self.valor is None or self.status == 'error':
            return self
        
        # Valida se é positivo
        if self.valor <= 0:
            logger.error(f'Valor deve ser positivo: {self.valor}')
            self.status = 'error'
            self.error_type = 'VALOR_INVALIDO'
            self.valor_issue = f'Valor deve ser maior que zero (informado: {self.valor})'
            self.valor = None
            return self
        
        # Se passou, formata e mantém validated
        self.valor_formatted = f"R$ {self.valor:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')
        logger.info(f"Valor validado: {self.valor_formatted}")
        return self

class DescricaoExtraida(CampoExtraido):
    """Dados da descrição extraída."""
    descricao_extracted: Optional[str] = None
    descricao: Optional[str] = None
    descricao_suggested: Optional[str] = None
    descricao_issue: Optional[str] = None
    error_type: Optional[str] = None
    status : Literal['validated', 'null', 'error', 'warning'] = 'null'  

    @model_validator(mode='after')
    def validar_descricao_completa(self):
        """Validação rigorosa de Descrição - BLOQUEIA dados inválidos."""
        
        # corrigir prompt que não completa descricao_extracted
        if not self.descricao:
            self.descricao = self.descricao_extracted
        
        # Se ainda está None/vazio após atribuição, retorna como null
        if not self.descricao or self.descricao.strip() == "":
            self.status = 'null'
            self.descricao = None
            return self
                    
        # Valida tamanho mínimo e máximo
        if len(self.descricao) < 10:
            logger.error(f'Descrição muito curta: {len(self.descricao)} caracteres')
            self.status = 'error'
            self.error_type = 'DESCRICAO_INVALIDA'
            self.descricao_issue = f'Descrição deve ter pelo menos 10 caracteres (informado: {len(self.descricao)})'
            self.descricao = None
            return self
        
        if len(self.descricao) > 500:
            logger.error(f'Descrição muito longa: {len(self.descricao)} caracteres')
            self.status = 'error'
            self.error_type = 'DESCRICAO_INVALIDA'
            self.descricao_issue = f'Descrição não pode exceder 500 caracteres (informado: {len(self.descricao)})'
            self.descricao = None
            return self
        
        logger.info(f"Descrição validada: {self.descricao[:50]}...")
        return self

class DadosNFSe(BaseModel):
    """
    Modelo completo de dados extraidos para emissão da NFSe.
    Representa o contrato entre AIExtractor e MessageProcessor
    """

    cnpj: CNPJExtraido = Field(default_factory=CNPJExtraido)
    valor: ValorExtraido = Field(default_factory=ValorExtraido)
    descricao: DescricaoExtraida = Field(default_factory=DescricaoExtraida)
    data_complete: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    invalid_fields: list[str] = Field(default_factory=list)
    user_message: str = ""

    @model_validator(mode='after')
    def validar_completude(self):
        """Recalcula data_complete, missing_fields e invalid_fields após validação de campos."""
        self.missing_fields = []
        self.invalid_fields = []
        
        # Verifica CNPJ
        if self.cnpj.status == 'null':
            self.missing_fields.append('cnpj')
        elif self.cnpj.status == 'error':
            self.invalid_fields.append(f"cnpj: {self.cnpj.cnpj_issue}")
        
        # Verifica Valor
        if self.valor.status == 'null':
            self.missing_fields.append('valor')
        elif self.valor.status == 'error':
            self.invalid_fields.append(f"valor: {self.valor.valor_issue}")
        
        # Verifica Descrição
        if self.descricao.status == 'null':
            self.missing_fields.append('descricao')
        elif self.descricao.status == 'error':
            self.invalid_fields.append(f"descricao: {self.descricao.descricao_issue}")
        
        # Define data_complete apenas se todos campos validated e nenhum error
        self.data_complete = (
            self.cnpj.status == 'validated' and
            self.valor.status == 'validated' and
            self.descricao.status == 'validated' and
            len(self.invalid_fields) == 0
        )
        #deixar a IA montar o prompt
        # Monta mensagem para usuário

        # Prioridade: erros de validação > user_message da IA > fallback
        if self.invalid_fields:
            self.user_message = "❌ Dados inválidos:\n" + "\n".join(f"• {msg}" for msg in self.invalid_fields)
        elif not self.user_message or not self.user_message.strip():
            # Fallback se a IA não gerou user_message
            if self.missing_fields:
                campos = ", ".join(self.missing_fields)
                self.user_message = f"Para emitir a nota, ainda preciso de: {campos}."
            elif self.data_complete:
                self.user_message = "Pronto! Vou preparar o espelho da nota para você confirmar."

        return self

    def is_valid(self) -> bool:
        """ Verifica se todos os campos estão validados"""
        return (
            self.cnpj.status == 'validated' and
            self.valor.status == 'validated' and
            self.descricao.status == 'validated'
        )
    
    def merge(self, novo: 'DadosNFSe') -> 'DadosNFSe':
        """
        Mescla dados novos com anteriores, priorizando lógica de recuperação.
        
        REGRAS DE MERGE:
        1. Se campo ANTERIOR tem erro → SEMPRE usa NOVO (permite correção)
        2. Se campo NOVO é 'validated' → SEMPRE usa NOVO (dado válido tem prioridade)
        3. Se campo NOVO é 'null' e ANTERIOR é 'validated' → mantém ANTERIOR
        4. Caso contrário → usa NOVO
        
        Args:
            novo: Novos dados extraídos da mensagem atual
            
        Returns:
            DadosNFSe mesclado com melhor conjunto de dados
        """
        
        # CNPJ: Prioriza validated, descarta erro
        if self.cnpj.status == 'error':
            # Anterior tinha erro → sempre tenta novo (mesmo que null)
            cnpj_final = novo.cnpj
            logger.info(f"CNPJ: descartando erro anterior, usando novo ({novo.cnpj.status})")
        elif novo.cnpj.status == 'validated':
            # Novo é válido → sempre usa
            cnpj_final = novo.cnpj
            logger.info(f"CNPJ: usando novo validado")
        elif novo.cnpj.status == 'null' and self.cnpj.status == 'validated':
            # Novo é null mas anterior válido → mantém anterior
            cnpj_final = self.cnpj
            logger.info(f"CNPJ: mantendo anterior validado")
        else:
            # Demais casos → usa novo
            cnpj_final = novo.cnpj
        
        # VALOR: Mesma lógica
        if self.valor.status == 'error':
            valor_final = novo.valor
            logger.info(f"Valor: descartando erro anterior, usando novo ({novo.valor.status})")
        elif novo.valor.status == 'validated':
            valor_final = novo.valor
            logger.info(f"Valor: usando novo validado")
        elif novo.valor.status == 'null' and self.valor.status == 'validated':
            valor_final = self.valor
            logger.info(f"Valor: mantendo anterior validado")
        else:
            valor_final = novo.valor
        
        # DESCRIÇÃO: Mesma lógica
        if self.descricao.status == 'error':
            descricao_final = novo.descricao
            logger.info(f"Descrição: descartando erro anterior, usando novo ({novo.descricao.status})")
        elif novo.descricao.status == 'validated':
            descricao_final = novo.descricao
            logger.info(f"Descrição: usando novo validado")
        elif novo.descricao.status == 'null' and self.descricao.status == 'validated':
            descricao_final = self.descricao
            logger.info(f"Descrição: mantendo anterior validado")
        else:
            descricao_final = novo.descricao
        
        return DadosNFSe(
            cnpj=cnpj_final,
            valor=valor_final,
            descricao=descricao_final,
            user_message=novo.user_message  # Preservar user_message da extração mais recente
            # data_complete, missing_fields, etc serão recalculados pelo validador
        )

    def to_dict(self) -> dict:
        """ Serializa para salvar no Redis """
        return self.model_dump(mode='json')
    
    @classmethod
    def from_dict(cls, data:dict) -> 'DadosNFSe':
        """ Deserializa do Redis """
        if not data:
            return cls()
        return cls.model_validate(data)
    
    # Em apps/core/models.py - adicionar no final da classe DadosNFSe

    def to_context(self) -> str:
        """
        Converte dados para contexto textual, para enviar como contexto para a IA, via prompt user
        Mostra valores validados para evitar pedidos repetidos.
        """

        logger.info("Convertendo dados para contexto textual")
        
        if not any([
            self.cnpj.status == 'validated',
            self.valor.status == 'validated', 
            self.descricao.status == 'validated'
        ]):
            logger.info("Nenhum campo validado - contexto vazio")
            return ""
        
        lines = []
        
        # CNPJ
        if self.cnpj.status == "validated":
            lines.append(f"CNPJ já informado: {self.cnpj.cnpj}")
        else:
            lines.append("CNPJ ainda não foi informado.")
        
        # Valor
        if self.valor.status == "validated":
            lines.append(f"Valor já informado: {self.valor.valor_formatted}")
        else:
            lines.append("Valor ainda não foi informado.")
        
        # Descrição
        if self.descricao.status == "validated":
            desc_preview = (self.descricao.descricao_extracted[:80] + "...") if len(self.descricao.descricao) > 80 else self.descricao.descricao
            lines.append(f"Descrição já informada: {desc_preview}")
        elif self.descricao.status == "warning":
            desc_preview = (self.descricao.descricao_extracted[:80] + "...") if len(self.descricao.descricao) > 80 else self.descricao.descricao
            lines.append(f"Descrição precisa ser confirmada: {desc_preview}")
        
        
        return "CONTEXTO ATUAL:\n" + "\n".join(f"- {line}" for line in lines)
    
## model session com pydantic v2

class Message(BaseModel):
    """Representa uma mensagem no histórico da conversa."""
    role: Literal['user', 'assistant', 'system']
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
class Session(BaseModel):
    """
    Sessão de conversa para emissão de NFSe.
    
    Armazena estado completo da interação incluindo:
    - Dados da nota em construção
    - Estado da máquina de estados
    - Histórico de mensagens
    - Métricas de uso
    """
    
    # Identificação
    sessao_id: str = Field(default_factory=lambda: f"{datetime.now().strftime('%d%m%y')}-{uuid4().hex[:4]}")
    telefone: str
    
    # Estado da máquina
    estado: Literal[
        'coleta',
        'dados_incompletos',
        'dados_completos',
        'aguardando_confirmacao',
        'processando',
        'aprovado',
        'rejeitado',
        'erro',
        'cancelado_usuario',
        'expirado'
    ] = 'coleta'
    
    # Dados da nota
    invoice_data: DadosNFSe = Field(default_factory=DadosNFSe)
    
    # Métricas
    interaction_count: int = 0  # Total de interações (user + bot)
    bot_message_count: int = 0  # Mensagens enviadas pelo bot
    ai_calls_count: int = 0  # Chamadas à API OpenAI
    
    # Histórico de conversa
    context: List[Message] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # TTL em segundos (padrão: 1 hora)
    ttl: int = 3600
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    # ==================== MÉTODOS DE CONVENIÊNCIA ====================
    
    def add_user_message(self, content: str) -> None:
        """Adiciona mensagem do usuário ao contexto."""
        self.context.append(Message(role='user', content=content))
        self.interaction_count += 1
        self.updated_at = datetime.now()
    
    def add_bot_message(self, content: str) -> None:
        """Adiciona mensagem do bot ao contexto."""
        self.context.append(Message(role='assistant', content=content))
        self.bot_message_count += 1
        self.interaction_count += 1
        self.updated_at = datetime.now()
    
    def add_system_message(self, content: str) -> None:
        """Adiciona mensagem do sistema ao contexto."""
        self.context.append(Message(role='system', content=content))
        self.updated_at = datetime.now()
    
    def increment_ai_calls(self) -> None:
        """Incrementa contador de chamadas à IA."""
        self.ai_calls_count += 1
        self.updated_at = datetime.now()
    
    def update_estado(self, novo_estado: str) -> None:
        """
        Atualiza estado da sessão com validação de transições.
        
        Args:
            novo_estado: Novo estado (deve ser valor válido de SessionState)
            
        Raises:
            ValueError: Se a transição não for válida
        """
        # Validar se transição é permitida
        if not is_valid_transition(self.estado, novo_estado):
            raise ValueError(
                f"Transição de estado inválida: {self.estado} → {novo_estado}. "
                f"Transições válidas: {list(s.value for s in SessionState if is_valid_transition(self.estado, s.value))}"
            )
        
        old_estado = self.estado
        self.estado = novo_estado
        self.updated_at = datetime.now()
        
        logger.info(
            f"Estado alterado: {old_estado} → {novo_estado}",
            extra={'sessao_id': self.sessao_id, 'telefone': self.telefone}
        )
        self.add_system_message(f"{datetime.now().strftime('%d/%m/%y %H:%M')} Estado alterado: {novo_estado}.")
        

    
    def update_invoice_data(self, dados: DadosNFSe) -> None:
        """Atualiza dados da nota."""
        self.invoice_data = dados
        self.updated_at = datetime.now()
        self.add_system_message(f"{datetime.now().strftime('%d/%m/%y %H:%M')} dados faltando: {dados.missing_fields}\ndados invalidos: {dados.invalid_fields}.")

    
    def get_conversation_history(self, limit: Optional[int] = None) -> List[Message]:
        """
        Retorna histórico de conversa.
        
        Args:
            limit: Limita quantidade de mensagens retornadas (mais recentes)
        """
        if limit:
            return self.context[-limit:]
        return self.context
    
    def get_age_seconds(self) -> float:
        """Retorna idade da sessão em segundos."""
        return (datetime.now() - self.created_at).total_seconds()
    
    def is_expired(self) -> bool:
        """Verifica se sessão expirou."""
        return self.get_age_seconds() > self.ttl
    
    # ==================== SERIALIZAÇÃO ====================
    
    def to_dict(self) -> dict:
        """Serializa para salvar no Redis."""
        return self.model_dump(mode='json')
    
    def to_json(self) -> str:
        """Serializa para JSON string."""
        return self.model_dump_json()
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Session':
        """Deserializa do Redis."""
        if not data:
            raise ValueError("Dados da sessão não podem ser vazios")
        return cls.model_validate(data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Session':
        """Deserializa de JSON string."""
        return cls.model_validate_json(json_str)