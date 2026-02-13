"""
Schema Pydantic para extracao focada.

DadosExtracao e o schema que a IA Extratora retorna.
NAO contem user_message - a resposta ao usuario e gerada pelo SmartResponseBuilder.

Apos extracao, converte para DadosNFSe (models.py existente) para validacao completa.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from decimal import Decimal

from apps.core.models import CNPJExtraido, ValorExtraido, DescricaoExtraida, DadosNFSe


class DadosExtracao(BaseModel):
    """
    Schema para structured output da IA Extratora.

    Apenas campos de extracao, sem user_message.
    A IA retorna isso, depois o Pydantic valida via DadosNFSe.
    """

    cnpj: CNPJExtraido = Field(default_factory=CNPJExtraido)
    valor: ValorExtraido = Field(default_factory=ValorExtraido)
    descricao: DescricaoExtraida = Field(default_factory=DescricaoExtraida)

    def to_dados_nfse(self) -> DadosNFSe:
        """
        Converte para DadosNFSe (modelo de dominio com validacao completa).

        DadosNFSe recalcula data_complete, missing_fields, invalid_fields
        automaticamente via model_validator.
        """
        return DadosNFSe(
            cnpj=self.cnpj,
            valor=self.valor,
            descricao=self.descricao,
            user_message=""  # sera gerado pelo SmartResponseBuilder
        )
