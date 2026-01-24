"""
Construtor de JSON para emissão de NFSe no padrão TecnoSpeed.
"""
from typing import Dict
import logging
from apps.nfse.models import NFSeEmissao

logger = logging.getLogger(__name__)


class NFSeBuilder:
    """Constrói JSON para emissão de NFSe."""
    
    @staticmethod
    def build_payload(emissao: NFSeEmissao) -> Dict:
        """
        Monta JSON para envio ao gateway TecnoSpeed.
        
        Args:
            emissao: Instância de NFSeEmissao
            
        Returns:
            Dicionário pronto para envio ao gateway
        """
        tomador = emissao.tomador
        prestador = emissao.prestador
        
        # Limpar CNPJ/CPF
        cpf_cnpj_prestador = ''.join(filter(str.isdigit, prestador.cpf_cnpj))
        
        payload = {
            "idIntegracao": emissao.id_integracao,
            "prestador": {
                "cpfCnpj": cpf_cnpj_prestador
            },
            "tomador": {
                "cpfCnpj": tomador.cnpj,
                "razaoSocial": tomador.razao_social,
                "inscricaoMunicipal": tomador.inscricao_municipal or "",
                "email": tomador.email or "",
                "endereco": {
                    "descricaoCidade": tomador.cidade,
                    "cep": tomador.cep,
                    "logradouro": tomador.logradouro,
                    "codigoCidade": tomador.codigo_cidade,
                    "complemento": tomador.complemento,
                    "estado": tomador.estado,
                    "numero": tomador.numero,
                    "bairro": tomador.bairro
                }
            },
            "servico": [{
                "codigo": emissao.codigo_servico,
                "codigoTributacao": emissao.codigo_tributacao,
                "discriminacao": emissao.descricao_servico,
                "cnae": emissao.cnae,
                "iss": {
                    "tipoTributacao": emissao.tipo_tributacao,
                    "exigibilidade": emissao.exigibilidade,
                    "aliquota": float(emissao.aliquota)
                },
                "valor": {
                    "servico": float(emissao.valor_servico),
                    "descontoCondicionado": float(emissao.desconto_condicionado),
                    "descontoIncondicionado": float(emissao.desconto_incondicionado)
                }
            }]
        }
        
        logger.info(f"Payload construído para {emissao.id_integracao}")
        logger.info(f"\n{50 * '='} INÍCIO EMISSÃO NFSe {50 * '='}\n")
        #log payload formatado
        logger.info(payload)
        logger.info(f"{50 * '='} FIM EMISSÃO NFSe {50 * '='}\n")

        return payload
