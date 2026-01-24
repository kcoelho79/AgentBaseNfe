"""
Serviço de consulta à Receita Federal via BrasilAPI.
"""
import httpx
import logging
from apps.nfse.models import ClienteTomador

logger = logging.getLogger(__name__)


class ReceitaFederalService:
    """Consulta dados de CNPJ na Receita Federal via BrasilAPI."""
    
    BASE_URL = "https://brasilapi.com.br/api/cnpj/v1"
    
    @classmethod
    def consultar_cnpj(cls, cnpj: str) -> dict:
        """
        Consulta CNPJ na Receita Federal.
        
        Args:
            cnpj: CNPJ (apenas números)
            
        Returns:
            Dicionário com dados do CNPJ
            
        Raises:
            httpx.HTTPStatusError: Se CNPJ não encontrado
        """
        # Remove formatação
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
        
        url = f"{cls.BASE_URL}/{cnpj_limpo}"
        logger.info(f"Consultando CNPJ na Receita Federal: {cnpj_limpo}")
        
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        
        dados = response.json()
        logger.info(f"CNPJ {cnpj_limpo} consultado com sucesso: {dados.get('razao_social')}")
        
        return dados
    
    @classmethod
    def buscar_ou_criar_tomador(cls, cnpj: str) -> ClienteTomador:
        """
        Busca tomador no banco ou consulta Receita e cria.
        
        Args:
            cnpj: CNPJ (apenas números ou formatado)
            
        Returns:
            Instância de ClienteTomador
        """
        # Limpar CNPJ
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))
        
        # Tenta buscar no banco
        tomador = ClienteTomador.objects.filter(cnpj=cnpj_limpo).first()
        if tomador:
            logger.info(f"Tomador {cnpj_limpo} encontrado no banco")
            return tomador
        
        # Consulta Receita Federal
        logger.info(f"Tomador {cnpj_limpo} não encontrado, consultando Receita...")
        dados = cls.consultar_cnpj(cnpj_limpo)
        
        # Cria novo tomador
        tomador = ClienteTomador.objects.create(
            cnpj=cnpj_limpo,
            razao_social=(dados.get('razao_social') or '')[:255],
            nome_fantasia=(dados.get('nome_fantasia') or '')[:255],
            email=(dados.get('email') or '')[:254],
            cep=(dados.get('cep') or '').replace('-', '')[:8],
            logradouro=(dados.get('logradouro') or '')[:255],
            numero=(dados.get('numero') or '')[:10],
            complemento=(dados.get('complemento') or '')[:100],
            bairro=(dados.get('bairro') or '')[:100],
            cidade=(dados.get('municipio') or '')[:100],
            codigo_cidade=str(dados.get('codigo_municipio_ibge') or '')[:7],
            estado=(dados.get('uf') or '')[:2],
            dados_receita_raw=dados
        )
        
        logger.info(f"Tomador {cnpj_limpo} criado: {tomador.razao_social}")
        return tomador
