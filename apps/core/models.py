from django.db import models

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal
from decimal import Decimal

import logging

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
        # Se não tem descrição ou já está em erro, não valida
        if not self.descricao or self.status == 'error':
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
        # deixar a IA montar o prompt
        # # Monta mensagem para usuário
        # if self.invalid_fields:
        #     self.user_message = "❌ Dados inválidos:\n" + "\n".join(f"• {field}" for field in self.invalid_fields)
        # elif self.missing_fields:
        #     self.user_message = "⚠️ Ainda falta:\n" + "\n".join(f"• {field}" for field in self.missing_fields)
        # else:
        #     self.user_message = "✅ Todos os dados foram coletados!"
        
        return self

    def is_valid(self) -> bool:
        """ Verifica se todos os campos estão validados"""
        return (
            self.cnpj.status == 'validated' and
            self.valor.status == 'validated' and
            self.descricao.status == 'validated'
        )
    
    def merge(self, cache: 'DadosNFSe') -> 'DadosNFSe':
        """
        Mescla com dados anterioes (estão cache Redis), preservando campos válidos

        Regra: Só substitui um campo anterior se o novo status != 'null'

        Args:
            cache: Outro objeto DadosNFSe para mesclar

        Returns:
            Novo objeto DadosNFSe mesclado
        """
        return DadosNFSe(
            cnpj=cache.cnpj if cache.cnpj.status != 'null' else self.cnpj,
            valor=cache.valor if cache.valor.status != 'null' else self.valor,
            descricao=cache.descricao if cache.descricao.status != 'null' else self.descricao,
            data_complete=cache.data_complete,
            missing_fields=cache.missing_fields,
            invalid_fields=cache.invalid_fields,
            user_message=cache.user_message

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
        if not any([
            self.cnpj.status != 'null',
            self.valor.status != 'null', 
            self.descricao.status != 'null'
        ]):
            return ""
        
        lines = []
        
        # CNPJ
        if self.cnpj.status == "validated":
            lines.append(f"CNPJ já informado: {self.cnpj.cnpj}")
        elif self.cnpj.status == "error":
            lines.append(f"CNPJ informado está com erro: {self.cnpj.cnpj_issue}")
        else:
            lines.append("CNPJ ainda não foi informado.")
        
        # Valor
        if self.valor.status == "validated":
            lines.append(f"Valor já informado: {self.valor.valor_formatted}")
        elif self.valor.status == "error":
            lines.append(f"Valor informado está com erro: {self.valor.valor_issue}")
        else:
            lines.append("Valor ainda não foi informado.")
        
        # Descrição
        if self.descricao.status == "validated":
            desc_preview = (self.descricao.descricao[:80] + "...") if len(self.descricao.descricao) > 80 else self.descricao.descricao
            lines.append(f"Descrição já informada: {desc_preview}")
        elif self.descricao.status == "warning":
            desc_preview = (self.descricao.descricao[:80] + "...") if len(self.descricao.descricao) > 80 else self.descricao.descricao
            lines.append(f"Descrição precisa ser confirmada: {desc_preview}")
        elif self.descricao.status == "error":
            lines.append(f"Descrição informada está com erro: {self.descricao.descricao_issue}")
        else:
            lines.append("Descrição ainda não foi informada.")
        
        return "CONTEXTO ATUAL:\n" + "\n".join(f"- {line}" for line in lines)