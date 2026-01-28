"""
Serviço de emissão de NFSe - Orquestra todo o processo.
"""
import uuid
import logging
from datetime import datetime
from django.utils import timezone
from apps.nfse.models import NFSeEmissao, NFSeProcessada, EmpresaClienteTomador
from apps.nfse.services.receita_federal import ReceitaFederalService
from apps.nfse.services.nfse_builder import NFSeBuilder
from apps.nfse.services.mock_gateway import MockNFSeGateway
from apps.core.db_models import SessionSnapshot
from apps.contabilidade.models import UsuarioEmpresa

logger = logging.getLogger(__name__)


class NFSeEmissaoService:
    """Orquestra emissão de NFSe."""
    
    @classmethod
    def emitir_de_sessao(cls, sessao_id: str) -> NFSeProcessada:
        """
        Emite NFSe a partir de uma sessão confirmada.
        
        Fluxo:
        1. Busca prestador (Empresa) pelo telefone da sessão
        2. Consulta tomador na Receita Federal
        3. Cria/atualiza vínculo Empresa-Tomador
        4. Cria registro de emissão
        5. Monta JSON
        6. Envia para gateway (mock)
        7. Processa retorno
        8. Cria NFSeProcessada
        
        Args:
            sessao_id: ID da sessão
            
        Returns:
            Instância de NFSeProcessada
            
        Raises:
            ValueError: Se dados inválidos
            Exception: Erros no processo
        """
        logger.info(f"{50 * '='} INÍCIO EMISSÃO NFSe {50 * '='}\n")
        logger.info(f"Iniciando emissão de NFSe para sessão {sessao_id}")
        
        # 1. Buscar sessão
        try:
            session = SessionSnapshot.objects.get(sessao_id=sessao_id)
        except SessionSnapshot.DoesNotExist:
            raise ValueError(f"Sessão {sessao_id} não encontrada")
        
        # 2. Buscar prestador (empresa) pelo telefone
        usuario_empresa = UsuarioEmpresa.objects.filter(
            telefone=session.telefone,
            is_active=True
        ).select_related('empresa').first()
        
        if not usuario_empresa:
            raise ValueError(f"Nenhuma empresa encontrada para telefone {session.telefone}")
        
        prestador = usuario_empresa.empresa
        logger.info(f"Prestador: {prestador.razao_social}")
        
        # 3. Buscar/criar tomador
        logger.info(f"Consultando tomador CNPJ: {session.cnpj}")
        tomador = ReceitaFederalService.buscar_ou_criar_tomador(session.cnpj)
        logger.info(f"Tomador: {tomador.razao_social}")
        
        # 4. Criar/atualizar vínculo Empresa-Tomador
        vinculo, created = EmpresaClienteTomador.objects.get_or_create(
            empresa=prestador,
            cliente_tomador=tomador,
            defaults={'is_active': True}
        )
        if created:
            logger.info(f"Vínculo criado: {prestador.razao_social} → {tomador.razao_social}")
        else:
            # Atualiza a data da última nota (campo auto_now)
            vinculo.save()
            logger.info(f"Vínculo atualizado: {prestador.razao_social} → {tomador.razao_social}")
        
        # 5. Criar registro de emissão
        id_integracao = f"NFSE-{uuid.uuid4().hex[:8].upper()}"
        
        emissao = NFSeEmissao.objects.create(
            session=session,
            prestador=prestador,
            tomador=tomador,
            id_integracao=id_integracao,
            descricao_servico=session.descricao or "Serviços prestados",
            valor_servico=session.valor,
            status='pendente'
        )
        logger.info(f"Emissão criada: {id_integracao}")
        
        # 6. Montar payload
        payload = NFSeBuilder.build_payload(emissao)
        emissao.payload_enviado = payload
        emissao.save()
        
        # 7. Enviar para gateway (mock)
        emissao.status = 'enviado'
        emissao.enviado_em = timezone.now()
        emissao.save()
        
        logger.info(f"Enviando para gateway mock...")
        resposta = MockNFSeGateway.emitir_nfse(payload)
        
        # 8. Processar retorno
        emissao.resposta_gateway = resposta
        emissao.status = 'processando'
        emissao.save()
        
        # 9. Criar NFSeProcessada
        nfse = cls._criar_nfse_processada(emissao, resposta)
        logger.info(f"NFSe processada criada: {nfse.numero}")
        
        # 10. Atualizar sessão
        session.id_integracao = id_integracao
        session.save()
        
        emissao.status = 'concluido'
        emissao.processado_em = timezone.now()
        emissao.save()
        
        logger.info(f"Emissão concluída: NFSe {nfse.numero}")
        logger.info(f"{50 * '='} FIM EMISSÃO NFSe {50 * '='}\n")

        return nfse
    
    @classmethod
    def _criar_nfse_processada(cls, emissao: NFSeEmissao, webhook_data: dict) -> NFSeProcessada:
        """
        Cria registro de NFSe processada a partir do retorno.
        
        Args:
            emissao: Instância de NFSeEmissao
            webhook_data: Dados retornados pelo gateway
            
        Returns:
            Instância de NFSeProcessada
        """
        nfse = NFSeProcessada.objects.create(
            emissao=emissao,
            id_externo=webhook_data['id'],
            numero=webhook_data['numero'],
            serie=webhook_data.get('serie', ''),
            chave=webhook_data['chave'],
            protocolo=webhook_data['protocolo'],
            status=webhook_data['status'],
            mensagem=webhook_data['mensagem'],
            c_stat=webhook_data['cStat'],
            emitente=webhook_data['emitente'],
            destinatario=webhook_data['destinatario'],
            valor=webhook_data['valor'],
            data_emissao=datetime.strptime(webhook_data['emissao'], '%d/%m/%Y').date(),
            data_autorizacao=datetime.strptime(webhook_data['dataAutorizacao'], '%d/%m/%Y').date(),
            url_xml=webhook_data.get('xml', ''),
            url_pdf=webhook_data.get('pdf', ''),
            destinada=webhook_data.get('destinada', False),
            documento=webhook_data.get('documento', 'nfse'),
            webhook_payload=webhook_data
        )
        
        return nfse
