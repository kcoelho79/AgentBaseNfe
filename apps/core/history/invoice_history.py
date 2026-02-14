import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

from django.db.models import Count, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


class InvoiceHistoryService:
    """
    Servico de historico de notas fiscais.

    Busca dados no banco de forma deterministica (sem IA).
    Todos os metodos recebem empresa_id para multi-tenancy.
    """

    @staticmethod
    def get_ultima_nota(empresa_id: int):
        """Retorna a ultima nota concluida da empresa."""
        from apps.nfse.models import NFSeEmissao

        return (
            NFSeEmissao.objects
            .filter(prestador_id=empresa_id, status='concluido')
            .select_related('tomador')
            .order_by('-created_at')
            .first()
        )

    @staticmethod
    def get_ultima_nota_para_cliente(empresa_id: int, cnpj_tomador: str):
        """Retorna a ultima nota concluida para um cliente especifico."""
        from apps.nfse.models import NFSeEmissao

        return (
            NFSeEmissao.objects
            .filter(
                prestador_id=empresa_id,
                status='concluido',
                tomador__cnpj=cnpj_tomador,
            )
            .select_related('tomador')
            .order_by('-created_at')
            .first()
        )

    @staticmethod
    def get_descricao_sugerida(empresa_id: int, cnpj_tomador: str) -> Optional[str]:
        """Retorna a descricao mais usada para um cliente."""
        from apps.nfse.models import NFSeEmissao

        resultado = (
            NFSeEmissao.objects
            .filter(
                prestador_id=empresa_id,
                status='concluido',
                tomador__cnpj=cnpj_tomador,
            )
            .values('descricao_servico')
            .annotate(count=Count('id'))
            .order_by('-count')
            .first()
        )

        if resultado:
            return resultado['descricao_servico']
        return None

    @staticmethod
    def get_resumo_mensal(empresa_id: int, mes: int = None, ano: int = None) -> dict:
        """
        Retorna resumo de notas do mes.

        Returns:
            dict com total_notas e valor_total
        """
        from apps.nfse.models import NFSeEmissao

        agora = timezone.now()
        mes = mes or agora.month
        ano = ano or agora.year

        qs = NFSeEmissao.objects.filter(
            prestador_id=empresa_id,
            status='concluido',
            created_at__year=ano,
            created_at__month=mes,
        )

        stats = qs.aggregate(
            total_notas=Count('id'),
            valor_total=Sum('valor_servico'),
        )

        return {
            'total_notas': stats['total_notas'] or 0,
            'valor_total': stats['valor_total'] or Decimal('0'),
            'mes': mes,
            'ano': ano,
        }

    @staticmethod
    def get_contexto_historico(empresa_id: int, limit: int = 3) -> str:
        """
        Gera texto compacto (~150 tokens) com historico recente.

        Formato:
        Ultimas notas: [razao_social] R$ X (DD/MM), ...
        """
        from apps.nfse.models import NFSeEmissao

        notas = (
            NFSeEmissao.objects
            .filter(prestador_id=empresa_id, status='concluido')
            .select_related('tomador')
            .order_by('-created_at')
            [:limit]
        )

        if not notas:
            return ""

        partes = []
        for nota in notas:
            nome = nota.tomador.razao_social if nota.tomador else "N/A"
            # Truncar nome longo
            if len(nome) > 30:
                nome = nome[:27] + "..."
            data = nota.created_at.strftime('%d/%m')
            partes.append(f"{nome} R$ {nota.valor_servico:,.2f} ({data})")

        return "Ultimas notas: " + ", ".join(partes)

    @staticmethod
    def dados_nfse_from_emissao(emissao):
        """
        Converte NFSeEmissao em DadosNFSe com todos campos 'validated'.

        Args:
            emissao: Instancia de NFSeEmissao com tomador carregado

        Returns:
            DadosNFSe preenchido
        """
        from apps.core.models import DadosNFSe, CNPJExtraido, ValorExtraido, DescricaoExtraida

        cnpj = CNPJExtraido(
            cnpj_extracted=emissao.tomador.cnpj,
            cnpj=emissao.tomador.cnpj,
            razao_social=emissao.tomador.razao_social,
            status='validated',
        )

        valor = ValorExtraido(
            valor_extracted=str(emissao.valor_servico),
            valor=emissao.valor_servico,
            valor_formatted=f"R$ {emissao.valor_servico:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'),
            status='validated',
        )

        descricao = DescricaoExtraida(
            descricao_extracted=emissao.descricao_servico,
            descricao=emissao.descricao_servico,
            status='validated',
        )

        return DadosNFSe(
            cnpj=cnpj,
            valor=valor,
            descricao=descricao,
        )
