import logging
from typing import Dict
from decimal import Decimal
from apps.nfse.models import ClienteTomador

logger = logging.getLogger(__name__)


class ResponseBuilder:
    """
    Constrói respostas para enviar ao cliente via WhatsApp.

    Formata mensagens para diferentes estados do fluxo:
    - Dados incompletos
    - Erros de validação
    - Espelho da nota (confirmação)
    - Confirmação de processamento
    - Nota aprovada
    - Erros
    - Cancelamento
    - Expiração
    """

    def build_dados_incompletos(self, user_message: str) -> str:
        """
        Mensagem solicitando dados faltantes.

        Args:
            User Message: mensagem resposta gerara pela IA Extractor

        Returns:
            Mensagem formatada
        """

        if user_message and user_message.strip():
            return user_message.strip()

        # Fallback se user_message estiver vazio
        logger.warning("user_message vazio - usando fallback")
        return "Para emitir a nota fiscal, preciso de algumas informações: CNPJ, valor e descrição do serviço."

    def build_validacao_erro(self, erros: list) -> str:
        """
        Mensagem de erro de validação.

        Args:
            erros: Lista de erros encontrados

        Returns:
            Mensagem formatada
        """
        erros_str = '\n'.join(f'• {erro}' for erro in erros)
        return f"""❌ *Dados Inválidos*

{erros_str}

Por favor, corrija e envie novamente.
Ou digite *cancelar* para cancelar.""".strip()

    # No reponse_builder.py - ajustar build_espelho:
    def build_espelho(self, dados: Dict, aliquota_iss: Decimal = Decimal('0.02')) -> str:
        if not dados:
            return "❌ Erro ao gerar espelho."
        
        # Extrair da estrutura do AIExtractor
        cnpj_obj = dados.get('cnpj', {})
        valor_obj = dados.get('valor', {})
        descricao_obj = dados.get('descricao', {})
        
        cnpj = cnpj_obj.get('cnpj_extracted', 'Não informado')
        valor = Decimal(str(valor_obj.get('valor', 0)))
        descricao = descricao_obj.get('descricao', 'Não informado')

        # Normaliza CNPJ (remove formatação)
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj)) if cnpj != 'Não informado' else ''
        
        # Busca razão social no banco
        razao_social = 'Não informado'
        if cnpj_limpo:
            tomador = ClienteTomador.objects.filter(cnpj=cnpj_limpo).first()
            if tomador:
                razao_social = tomador.razao_social
        
        valor_iss = valor * aliquota_iss
        
        return f"""📋 *ESPELHO DA NOTA FISCAL*

*Razao Social:* {razao_social}
*CNPJ:* {cnpj}

*Descrição:* {descricao}

*Valor dos Serviços:* R$ {valor:.2f}
*ISS ({aliquota_iss * 100:.0f}%):* R$ {valor_iss:.2f}

━━━━━━━━━━━━━━━━━━━━
*VALOR TOTAL:* R$ {valor:.2f}

✅ Confirma a emissão desta nota?

Digite *SIM* para confirmar
Digite *NÃO* para cancelar"""

    def build_confirmacao_processando(self, numero_protocolo: str) -> str:
        """
        Mensagem de confirmação - nota em processamento.

        Args:
            numero_protocolo: Número do protocolo

        Returns:
            Mensagem formatada
        """
        return f"""✅ *Nota Fiscal em Processamento!*

Você receberá o PDF em alguns instantes.

📝 Protocolo: {numero_protocolo}""".strip()

    def build_nota_aprovada(self, numero_nfe: str) -> str:
        """
        Mensagem de nota aprovada.

        Args:
            numero_nfe: Número da NFSe

        Returns:
            Mensagem formatada
        """
        return f"""🎉 *Nota Fiscal Emitida com Sucesso!*

Número da NFSe: *{numero_nfe}*

O PDF está sendo enviado...""".strip()

    def build_nota_erro(self, erro: str) -> str:
        """
        Mensagem de erro na emissão.

        Args:
            erro: Descrição do erro

        Returns:
            Mensagem formatada
        """
        return f"""❌ *Erro ao Emitir Nota Fiscal*

{erro}

Por favor, entre em contato com sua contabilidade.""".strip()

    def build_cancelado(self) -> str:
        """
        Mensagem de operação cancelada.

        Returns:
            Mensagem formatada
        """
        return """ ❌ *EMISSÃO CANCELADA*
Os dados foram descartados
Para emitir uma nova nota fiscal, envie novamente as informações:

CNPJ
Valor
Descrição

Envie uma nova mensagem quando precisar emitir uma nota."""
    
    def build_nfse_emitida(self, nfse) -> str:
        """
        Mensagem de NFSe emitida com sucesso.
        
        Args:
            nfse: Instância de NFSeProcessada
            
        Returns:
            Mensagem formatada
        """
        return f"""✅ *NOTA FISCAL EMITIDA COM SUCESSO!*

📄 *Número:* {nfse.numero}
📅 *Emissão:* {nfse.data_emissao.strftime('%d/%m/%Y')}
💰 *Valor:* R$ {nfse.valor:,.2f}

🔑 *Chave:* {nfse.chave}
📋 *Protocolo:* {nfse.protocolo}

📥 *Links para Download:*
• PDF: {nfse.url_pdf}
• XML: {nfse.url_xml}

✨ Obrigado por utilizar nossos serviços!"""

    def build_expirado(self) -> str:
        """
        Mensagem de sessão expirada.

        Returns:
            Mensagem formatada
        """
        return """⏱️ *Tempo Esgotado*

A solicitação de nota fiscal expirou.
Envie uma nova mensagem para recomeçar.""".strip()

    def build_boas_vindas(self, nome_cliente: str) -> str:
        """
        Mensagem de boas-vindas para novo cliente.

        Args:
            nome_cliente: Nome do cliente

        Returns:
            Mensagem formatada
        """
        return f"""👋 Olá, {nome_cliente}!

Seja bem-vindo ao sistema de emissão de notas fiscais.

Para emitir uma nota, envie uma mensagem com as informações:
• Valor
• Nome/Razão Social do tomador
• CNPJ do tomador
• Descrição do serviço

Exemplo:
_"Emitir nota de 1500 reais para Empresa XYZ CNPJ 12.345.678/0001-90 serviço de consultoria"_""".strip()
