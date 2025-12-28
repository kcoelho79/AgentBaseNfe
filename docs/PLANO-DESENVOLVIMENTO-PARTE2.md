# PLANO DE DESENVOLVIMENTO - AgentBase NFe (PARTE 2)

**Continuação dos Sprints 7-12**

---

## SPRINT 7: App NFe - Parte 1 (Models e Admin)

**Objetivo:** Criar models de Nota Fiscal e Certificado Digital
**Duração estimada:** 3-4 dias

### 7.1 Criação do App NFe

- [ ] **7.1.1** Criar app nfe
  - Executar: `python manage.py startapp nfe apps/nfe`

- [ ] **7.1.2** Registrar no `settings.py`
  ```python
  INSTALLED_APPS = [
      # ...
      'apps.nfe',
  ]
  ```

- [ ] **7.1.3** Criar estrutura de diretórios
  - Criar: `apps/nfe/services/`
  - Criar: `apps/nfe/integrations/`
  - Criar: `apps/nfe/integrations/tecnospeed/`
  - Criar: `apps/nfe/tasks.py`
  - Criar: `apps/nfe/templates/nfe/`

### 7.2 Models do NFe

- [ ] **7.2.1** Criar choices em `apps/nfe/models.py`
  ```python
  import uuid
  from django.db import models
  from decimal import Decimal

  class StatusNotaFiscalChoices(models.TextChoices):
      RASCUNHO = 'rascunho', 'Rascunho'
      PROCESSANDO = 'processando', 'Processando'
      ENVIADO_GATEWAY = 'enviado_gateway', 'Enviado ao Gateway'
      APROVADO = 'aprovado', 'Aprovado'
      REJEITADO = 'rejeitado', 'Rejeitado'
      CANCELADO = 'cancelado', 'Cancelado'
      ERRO = 'erro', 'Erro'

  class TipoCertificadoChoices(models.TextChoices):
      A1 = 'A1', 'A1 (arquivo)'
      A3 = 'A3', 'A3 (token/cartão)'

  class StatusCertificadoChoices(models.TextChoices):
      ATIVO = 'ativo', 'Ativo'
      VENCIDO = 'vencido', 'Vencido'
      REVOGADO = 'revogado', 'Revogado'
  ```

- [ ] **7.2.2** Criar model `CertificadoDigital`
  ```python
  class CertificadoDigital(models.Model):
      id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

      contabilidade = models.ForeignKey(
          'contabilidade.Contabilidade',
          on_delete=models.PROTECT,
          related_name='certificados',
          verbose_name='Contabilidade'
      )

      # Arquivo do certificado (criptografado)
      certificado_arquivo = models.BinaryField('Arquivo do Certificado')
      senha = models.CharField('Senha', max_length=255)  # Será criptografada

      validade = models.DateField('Validade')
      tipo = models.CharField(
          'Tipo',
          max_length=2,
          choices=TipoCertificadoChoices.choices,
          default=TipoCertificadoChoices.A1
      )

      status = models.CharField(
          'Status',
          max_length=20,
          choices=StatusCertificadoChoices.choices,
          default=StatusCertificadoChoices.ATIVO
      )

      is_active = models.BooleanField('Ativo', default=True)
      created_at = models.DateTimeField(auto_now_add=True)
      updated_at = models.DateTimeField(auto_now=True)

      class Meta:
          db_table = 'certificado_digital'
          verbose_name = 'Certificado Digital'
          verbose_name_plural = 'Certificados Digitais'
          ordering = ['-created_at']

      def __str__(self):
          return f'Certificado {self.tipo} - {self.contabilidade}'

      def esta_valido(self):
          """Verifica se certificado está válido."""
          from django.utils import timezone
          return (
              self.is_active and
              self.status == StatusCertificadoChoices.ATIVO and
              self.validade >= timezone.now().date()
          )
  ```

- [ ] **7.2.3** Criar model `NotaFiscal`
  ```python
  class NotaFiscal(models.Model):
      id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

      # Relacionamentos
      contabilidade = models.ForeignKey(
          'contabilidade.Contabilidade',
          on_delete=models.PROTECT,
          related_name='notas_fiscais',
          verbose_name='Contabilidade'
      )

      cliente_contabilidade = models.ForeignKey(
          'contabilidade.ClienteContabilidade',
          on_delete=models.PROTECT,
          related_name='notas_fiscais',
          verbose_name='Cliente'
      )

      protocolo = models.ForeignKey(
          'core.Protocolo',
          on_delete=models.SET_NULL,
          null=True,
          blank=True,
          related_name='nota_fiscal',
          verbose_name='Protocolo'
      )

      # Dados do Prestador (pega do cliente)
      cnpj_prestador = models.CharField('CNPJ Prestador', max_length=14)
      razao_social_prestador = models.CharField('Razão Social Prestador', max_length=255)
      inscricao_municipal_prestador = models.CharField('Inscrição Municipal', max_length=20, blank=True)

      # Dados do Tomador
      cnpj_tomador = models.CharField('CNPJ Tomador', max_length=14)
      razao_social_tomador = models.CharField('Razão Social Tomador', max_length=255)

      # Dados da Nota
      valor = models.DecimalField('Valor', max_digits=15, decimal_places=2)
      descricao = models.TextField('Descrição do Serviço')
      codigo_servico_municipal = models.CharField('Código Serviço Municipal', max_length=10)

      # Tributos
      aliquota_iss = models.DecimalField('Alíquota ISS', max_digits=5, decimal_places=4)
      valor_iss = models.DecimalField('Valor ISS', max_digits=15, decimal_places=2)
      valor_liquido = models.DecimalField(
          'Valor Líquido',
          max_digits=15,
          decimal_places=2,
          help_text='Valor - ISS'
      )

      # Retorno do Gateway
      numero_nfe = models.CharField('Número NFSe', max_length=20, blank=True)
      codigo_verificacao = models.CharField('Código Verificação', max_length=100, blank=True)
      xml_nfse = models.TextField('XML NFSe', blank=True)
      pdf_nfse = models.BinaryField('PDF NFSe', blank=True)

      # Controle
      status = models.CharField(
          'Status',
          max_length=20,
          choices=StatusNotaFiscalChoices.choices,
          default=StatusNotaFiscalChoices.RASCUNHO
      )
      error_message = models.TextField('Mensagem de Erro', blank=True)
      tentativas_emissao = models.IntegerField('Tentativas de Emissão', default=0)

      # Timestamps
      created_at = models.DateTimeField('Criado em', auto_now_add=True)
      updated_at = models.DateTimeField('Atualizado em', auto_now=True)
      emitida_em = models.DateTimeField('Emitida em', null=True, blank=True)
      cancelada_em = models.DateTimeField('Cancelada em', null=True, blank=True)

      class Meta:
          db_table = 'nota_fiscal'
          verbose_name = 'Nota Fiscal'
          verbose_name_plural = 'Notas Fiscais'
          ordering = ['-created_at']
          indexes = [
              models.Index(fields=['contabilidade', '-created_at']),
              models.Index(fields=['cliente_contabilidade', '-created_at']),
              models.Index(fields=['status']),
              models.Index(fields=['numero_nfe']),
          ]

      def __str__(self):
          return f'NFe {self.numero_nfe or self.id}'

      def save(self, *args, **kwargs):
          # Calcular valor líquido
          if self.valor and self.valor_iss:
              self.valor_liquido = self.valor - self.valor_iss
          super().save(*args, **kwargs)
  ```

- [ ] **7.2.4** Criar model `HistoricoNota`
  ```python
  class HistoricoNota(models.Model):
      """
      Registro de todas as alterações de estado da nota.
      """
      id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

      nota_fiscal = models.ForeignKey(
          NotaFiscal,
          on_delete=models.CASCADE,
          related_name='historico',
          verbose_name='Nota Fiscal'
      )

      status_anterior = models.CharField('Status Anterior', max_length=20)
      status_novo = models.CharField('Status Novo', max_length=20)

      observacao = models.TextField('Observação', blank=True)
      dados_extras = models.JSONField('Dados Extras', default=dict, blank=True)

      usuario = models.ForeignKey(
          'account.User',
          on_delete=models.SET_NULL,
          null=True,
          blank=True,
          verbose_name='Usuário'
      )

      created_at = models.DateTimeField(auto_now_add=True)

      class Meta:
          db_table = 'historico_nota'
          verbose_name = 'Histórico de Nota'
          verbose_name_plural = 'Históricos de Notas'
          ordering = ['-created_at']

      def __str__(self):
          return f'{self.status_anterior} → {self.status_novo}'
  ```

### 7.3 Signals para Histórico

- [ ] **7.3.1** Criar `apps/nfe/signals.py`
  ```python
  from django.db.models.signals import post_save, pre_save
  from django.dispatch import receiver
  from .models import NotaFiscal, HistoricoNota

  @receiver(pre_save, sender=NotaFiscal)
  def registrar_mudanca_status(sender, instance, **kwargs):
      """
      Registra mudanças de status no histórico.
      """
      if instance.pk:
          try:
              nota_antiga = NotaFiscal.objects.get(pk=instance.pk)
              if nota_antiga.status != instance.status:
                  # Criar registro no histórico
                  HistoricoNota.objects.create(
                      nota_fiscal=instance,
                      status_anterior=nota_antiga.status,
                      status_novo=instance.status,
                      observacao=f'Status alterado de {nota_antiga.status} para {instance.status}'
                  )
          except NotaFiscal.DoesNotExist:
              pass

  @receiver(post_save, sender=NotaFiscal)
  def incrementar_metricas(sender, instance, created, **kwargs):
      """
      Incrementa métricas do cliente quando nota é aprovada.
      """
      if instance.status == 'aprovado' and instance.emitida_em:
          # Verificar se já incrementou
          if not hasattr(instance, '_metricas_incrementadas'):
              instance.cliente_contabilidade.incrementar_metricas(instance.valor)
              instance._metricas_incrementadas = True
  ```

- [ ] **7.3.2** Registrar signals no `apps/nfe/apps.py`
  ```python
  from django.apps import AppConfig

  class NfeConfig(AppConfig):
      default_auto_field = 'django.db.models.BigAutoField'
      name = 'apps.nfe'
      verbose_name = 'Nota Fiscal Eletrônica'

      def ready(self):
          import apps.nfe.signals
  ```

### 7.4 Admin do NFe

- [ ] **7.4.1** Registrar models em `apps/nfe/admin.py`
  ```python
  from django.contrib import admin
  from django.utils.html import format_html
  from .models import NotaFiscal, CertificadoDigital, HistoricoNota

  class HistoricoNotaInline(admin.TabularInline):
      model = HistoricoNota
      extra = 0
      readonly_fields = ['status_anterior', 'status_novo', 'observacao', 'created_at', 'usuario']
      can_delete = False

  @admin.register(NotaFiscal)
  class NotaFiscalAdmin(admin.ModelAdmin):
      list_display = [
          'numero_nfe_display', 'cliente_contabilidade',
          'valor', 'status_badge', 'created_at'
      ]
      list_filter = ['status', 'created_at', 'contabilidade']
      search_fields = [
          'numero_nfe', 'cnpj_tomador',
          'razao_social_tomador', 'descricao'
      ]
      readonly_fields = [
          'created_at', 'updated_at', 'emitida_em',
          'numero_nfe', 'codigo_verificacao'
      ]

      inlines = [HistoricoNotaInline]

      fieldsets = (
          ('Identificação', {
              'fields': (
                  'contabilidade', 'cliente_contabilidade',
                  'protocolo', 'numero_nfe', 'codigo_verificacao'
              )
          }),
          ('Prestador', {
              'fields': (
                  'cnpj_prestador', 'razao_social_prestador',
                  'inscricao_municipal_prestador'
              )
          }),
          ('Tomador', {
              'fields': ('cnpj_tomador', 'razao_social_tomador')
          }),
          ('Serviço', {
              'fields': (
                  'descricao', 'codigo_servico_municipal',
                  'valor', 'aliquota_iss', 'valor_iss', 'valor_liquido'
              )
          }),
          ('Status', {
              'fields': (
                  'status', 'error_message',
                  'tentativas_emissao'
              )
          }),
          ('Datas', {
              'fields': (
                  'created_at', 'updated_at',
                  'emitida_em', 'cancelada_em'
              )
          }),
      )

      def numero_nfe_display(self, obj):
          return obj.numero_nfe or '—'
      numero_nfe_display.short_description = 'Número NFSe'

      def status_badge(self, obj):
          colors = {
              'rascunho': 'gray',
              'processando': 'blue',
              'aprovado': 'green',
              'rejeitado': 'red',
              'erro': 'red',
              'cancelado': 'orange',
          }
          color = colors.get(obj.status, 'gray')
          return format_html(
              '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
              color, obj.get_status_display()
          )
      status_badge.short_description = 'Status'

  @admin.register(CertificadoDigital)
  class CertificadoDigitalAdmin(admin.ModelAdmin):
      list_display = [
          'contabilidade', 'tipo', 'validade',
          'status', 'is_active'
      ]
      list_filter = ['tipo', 'status', 'is_active']
      search_fields = ['contabilidade__nome_fantasia']

      fieldsets = (
          ('Tenant', {
              'fields': ('contabilidade',)
          }),
          ('Certificado', {
              'fields': ('tipo', 'validade', 'status', 'is_active'),
              'description': 'Arquivo do certificado é armazenado criptografado'
          }),
          ('Datas', {
              'fields': ('created_at', 'updated_at')
          }),
      )

      readonly_fields = ['created_at', 'updated_at']

      # Ocultar campos sensíveis
      exclude = ['certificado_arquivo', 'senha']
  ```

### 7.5 Migrations

- [ ] **7.5.1** Criar migrations
  - Executar: `python manage.py makemigrations nfe`

- [ ] **7.5.2** Aplicar migrations
  - Executar: `python manage.py migrate`

- [ ] **7.5.3** Verificar tabelas criadas
  - Executar: `psql -U postgres -d agentbase_nfe`
  - Executar: `\dt`
  - Verificar: `nota_fiscal`, `certificado_digital`, `historico_nota`

### 7.6 Testes Básicos

- [ ] **7.6.1** Criar nota fiscal de teste no admin
- [ ] **7.6.2** Verificar criação de histórico
- [ ] **7.6.3** Testar filtros e buscas no admin

---

## SPRINT 8: App NFe - Parte 2 (Services e Integração)

**Objetivo:** Implementar serviços de emissão e integração com Tecnospeed
**Duração estimada:** 4-5 dias

### 8.1 RPS Builder Service

- [ ] **8.1.1** Criar `RPSBuilder` em `apps/nfe/services/rps_builder.py`
  ```python
  import logging
  from xml.etree.ElementTree import Element, SubElement, tostring
  from apps.nfe.models import NotaFiscal

  logger = logging.getLogger(__name__)

  class RPSBuilder:
      """
      Constrói XML RPS (Recibo Provisório de Serviço).
      """

      def build_rps_xml(self, nota_fiscal: NotaFiscal) -> str:
          """
          Constrói XML RPS.
          """
          logger.info(f'Construindo RPS para nota {nota_fiscal.id}')

          # Root
          rps = Element('RPS')

          # Identificação RPS
          identificacao = SubElement(rps, 'IdentificacaoRPS')
          SubElement(identificacao, 'Numero').text = str(nota_fiscal.id)
          SubElement(identificacao, 'Serie').text = 'RPS'
          SubElement(identificacao, 'Tipo').text = '1'

          # Prestador
          prestador = SubElement(rps, 'Prestador')
          SubElement(prestador, 'CNPJ').text = nota_fiscal.cnpj_prestador
          SubElement(prestador, 'InscricaoMunicipal').text = nota_fiscal.inscricao_municipal_prestador

          # Tomador
          tomador = SubElement(rps, 'Tomador')
          SubElement(tomador, 'CNPJ').text = nota_fiscal.cnpj_tomador
          SubElement(tomador, 'RazaoSocial').text = nota_fiscal.razao_social_tomador

          # Serviço
          servico = SubElement(rps, 'Servico')
          SubElement(servico, 'CodigoServico').text = nota_fiscal.codigo_servico_municipal
          SubElement(servico, 'Discriminacao').text = nota_fiscal.descricao
          SubElement(servico, 'ValorServicos').text = f'{nota_fiscal.valor:.2f}'
          SubElement(servico, 'AliquotaISS').text = f'{nota_fiscal.aliquota_iss:.4f}'
          SubElement(servico, 'ValorISS').text = f'{nota_fiscal.valor_iss:.2f}'

          # Converter para string
          xml_string = tostring(rps, encoding='unicode', method='xml')

          logger.debug('RPS XML construído')
          return xml_string
  ```

### 8.2 Certificate Manager Service

- [ ] **8.2.1** Adicionar biblioteca de criptografia
  ```bash
  pip install cryptography==41.0.7
  ```

- [ ] **8.2.2** Adicionar ao `requirements/base.txt`
  ```
  cryptography==41.0.7
  ```

- [ ] **8.2.3** Criar `CertificateManager` em `apps/nfe/services/certificate_manager.py`
  ```python
  import logging
  from cryptography.fernet import Fernet
  from django.conf import settings

  logger = logging.getLogger(__name__)

  class CertificateManager:
      """
      Gerencia certificados digitais com criptografia.
      """

      def __init__(self):
          # Chave de criptografia (deve estar no .env)
          key = settings.CERTIFICATE_ENCRYPTION_KEY.encode()
          self.cipher = Fernet(key)

      def encrypt_certificate(self, certificate_data: bytes) -> bytes:
          """Criptografa certificado."""
          return self.cipher.encrypt(certificate_data)

      def decrypt_certificate(self, encrypted_data: bytes) -> bytes:
          """Descriptografa certificado."""
          return self.cipher.decrypt(encrypted_data)

      def encrypt_password(self, password: str) -> str:
          """Criptografa senha."""
          return self.cipher.encrypt(password.encode()).decode()

      def decrypt_password(self, encrypted_password: str) -> str:
          """Descriptografa senha."""
          return self.cipher.decrypt(encrypted_password.encode()).decode()
  ```

- [ ] **8.2.4** Adicionar configuração no `settings.py`
  ```python
  # Gerar chave: from cryptography.fernet import Fernet; print(Fernet.generate_key())
  CERTIFICATE_ENCRYPTION_KEY = config('CERTIFICATE_ENCRYPTION_KEY')
  ```

- [ ] **8.2.5** Adicionar ao `.env`
  ```
  CERTIFICATE_ENCRYPTION_KEY=your-fernet-key-here
  ```

### 8.3 Fake Tecnospeed Client

- [ ] **8.3.1** Criar `FakeTecnospeedClient` em `apps/nfe/integrations/tecnospeed/fake_client.py`
  ```python
  import logging
  import random
  import base64
  from time import sleep
  from typing import Dict

  logger = logging.getLogger(__name__)

  class FakeTecnospeedClient:
      """
      Mock do cliente Tecnospeed para desenvolvimento.
      Simula respostas sem fazer chamadas reais.
      """

      def __init__(self):
          self.success_rate = 0.9  # 90% de sucesso

      def enviar_rps(
          self,
          rps_xml: str,
          certificado_pfx: bytes,
          senha_certificado: str
      ) -> Dict:
          """
          Simula envio de RPS.
          """
          logger.info('[FAKE] Simulando envio de RPS')

          # Simular latência
          sleep(random.uniform(1, 3))

          # Simular sucesso/erro
          if random.random() < self.success_rate:
              numero_nfe = f'NFE{random.randint(10000, 99999)}'
              codigo_verificacao = f'{random.randint(100000, 999999)}'

              logger.info(f'[FAKE] RPS enviado com sucesso: {numero_nfe}')

              return {
                  'sucesso': True,
                  'numero_nfe': numero_nfe,
                  'codigo_verificacao': codigo_verificacao,
                  'xml_nfse': self._gerar_xml_fake(numero_nfe),
                  'pdf_nfse': self._gerar_pdf_fake()
              }
          else:
              erros = [
                  'Certificado inválido',
                  'CNPJ do prestador não autorizado',
                  'RPS duplicado',
                  'Serviço temporariamente indisponível',
                  'Código de serviço inválido'
              ]
              erro = random.choice(erros)

              logger.warning(f'[FAKE] Erro ao enviar RPS: {erro}')

              return {
                  'sucesso': False,
                  'erro': erro,
                  'codigo_erro': random.randint(100, 999)
              }

      def consultar_nfse(self, numero_nfe: str, cnpj_prestador: str) -> Dict:
          """Simula consulta de NFSe."""
          logger.info(f'[FAKE] Consultando NFSe {numero_nfe}')

          sleep(random.uniform(0.5, 1.5))

          return {
              'sucesso': True,
              'numero_nfe': numero_nfe,
              'status': 'aprovada',
              'xml_nfse': self._gerar_xml_fake(numero_nfe),
              'pdf_nfse': self._gerar_pdf_fake()
          }

      def _gerar_xml_fake(self, numero_nfe: str) -> str:
          """Gera XML fake."""
          return f'''<?xml version="1.0" encoding="UTF-8"?>
  <NFSe>
      <NumeroNFSe>{numero_nfe}</NumeroNFSe>
      <DataEmissao>2025-01-01</DataEmissao>
      <Status>Aprovada</Status>
  </NFSe>'''

      def _gerar_pdf_fake(self) -> bytes:
          """Gera PDF fake em base64."""
          # Simulação de PDF
          fake_pdf = b'%PDF-1.4 FAKE PDF CONTENT'
          return base64.b64encode(fake_pdf)
  ```

### 8.4 NFe Emitter Service

- [ ] **8.4.1** Criar `NFeEmitter` em `apps/nfe/services/nfe_emitter.py`
  ```python
  import logging
  from typing import Dict
  from decimal import Decimal
  from django.utils import timezone
  from apps.nfe.models import NotaFiscal, CertificadoDigital, StatusNotaFiscalChoices
  from apps.contabilidade.models import ClienteContabilidade
  from .rps_builder import RPSBuilder
  from .certificate_manager import CertificateManager
  from ..integrations.tecnospeed.fake_client import FakeTecnospeedClient

  logger = logging.getLogger(__name__)

  class NFeEmitter:
      """
      Serviço de emissão de NFSe.
      """

      def __init__(self):
          self.rps_builder = RPSBuilder()
          self.cert_manager = CertificateManager()
          # TODO: Usar client real quando disponível
          self.gateway_client = FakeTecnospeedClient()

      def emitir(self, nota_fiscal_id: str) -> Dict:
          """
          Emite nota fiscal.

          Returns:
              Dict com resultado da emissão
          """
          logger.info(f'Iniciando emissão de nota {nota_fiscal_id}')

          try:
              # 1. Buscar nota fiscal
              nota = NotaFiscal.objects.select_related(
                  'cliente_contabilidade__empresa',
                  'contabilidade'
              ).get(id=nota_fiscal_id)

              # 2. Validar
              self._validar_nota(nota)

              # 3. Buscar certificado
              certificado = self._get_certificado_ativo(nota.contabilidade)

              # 4. Preencher dados do prestador (se não preenchidos)
              self._preencher_dados_prestador(nota)

              # 5. Montar RPS
              rps_xml = self.rps_builder.build_rps_xml(nota)

              # 6. Descriptografar certificado
              cert_data = self.cert_manager.decrypt_certificate(certificado.certificado_arquivo)
              cert_senha = self.cert_manager.decrypt_password(certificado.senha)

              # 7. Atualizar status
              nota.status = StatusNotaFiscalChoices.ENVIADO_GATEWAY
              nota.tentativas_emissao += 1
              nota.save()

              # 8. Enviar para gateway
              response = self.gateway_client.enviar_rps(
                  rps_xml=rps_xml,
                  certificado_pfx=cert_data,
                  senha_certificado=cert_senha
              )

              # 9. Processar retorno
              if response['sucesso']:
                  return self._processar_sucesso(nota, response)
              else:
                  return self._processar_erro(nota, response)

          except Exception as e:
              logger.exception('Erro na emissão')
              return {
                  'sucesso': False,
                  'erro': str(e)
              }

      def _validar_nota(self, nota: NotaFiscal):
          """Valida nota antes de emitir."""
          if nota.status not in [
              StatusNotaFiscalChoices.RASCUNHO,
              StatusNotaFiscalChoices.ERRO
          ]:
              raise ValueError(f'Nota em status inválido: {nota.status}')

          if not nota.contabilidade.pode_emitir_nota():
              raise ValueError('Contabilidade não pode emitir notas')

      def _get_certificado_ativo(self, contabilidade):
          """Busca certificado ativo."""
          certificado = CertificadoDigital.objects.filter(
              contabilidade=contabilidade,
              is_active=True
          ).first()

          if not certificado:
              raise ValueError('Nenhum certificado ativo encontrado')

          if not certificado.esta_valido():
              raise ValueError('Certificado vencido ou inválido')

          return certificado

      def _preencher_dados_prestador(self, nota: NotaFiscal):
          """Preenche dados do prestador da empresa do cliente."""
          empresa = nota.cliente_contabilidade.empresa

          if not nota.cnpj_prestador:
              nota.cnpj_prestador = empresa.cnpj

          if not nota.razao_social_prestador:
              nota.razao_social_prestador = empresa.razao_social

          if not nota.inscricao_municipal_prestador:
              nota.inscricao_municipal_prestador = empresa.inscricao_municipal

          nota.save(update_fields=[
              'cnpj_prestador',
              'razao_social_prestador',
              'inscricao_municipal_prestador'
          ])

      def _processar_sucesso(self, nota: NotaFiscal, response: Dict) -> Dict:
          """Processa retorno de sucesso."""
          logger.info(f'Nota {nota.id} emitida com sucesso')

          # Atualizar nota
          nota.numero_nfe = response['numero_nfe']
          nota.codigo_verificacao = response['codigo_verificacao']
          nota.xml_nfse = response['xml_nfse']
          nota.pdf_nfse = response['pdf_nfse']
          nota.status = StatusNotaFiscalChoices.APROVADO
          nota.emitida_em = timezone.now()
          nota.error_message = ''
          nota.save()

          return {
              'sucesso': True,
              'numero_nfe': nota.numero_nfe,
              'codigo_verificacao': nota.codigo_verificacao
          }

      def _processar_erro(self, nota: NotaFiscal, response: Dict) -> Dict:
          """Processa retorno de erro."""
          logger.warning(f'Erro ao emitir nota {nota.id}: {response.get("erro")}')

          # Atualizar nota
          nota.status = StatusNotaFiscalChoices.REJEITADO
          nota.error_message = response.get('erro', 'Erro desconhecido')
          nota.save()

          return {
              'sucesso': False,
              'erro': nota.error_message
          }
  ```

### 8.5 Celery Task de Emissão

- [ ] **8.5.1** Criar task em `apps/nfe/tasks.py`
  ```python
  from celery import shared_task
  import logging
  from .services.nfe_emitter import NFeEmitter
  from .models import NotaFiscal, StatusNotaFiscalChoices
  from apps.core.integrations.whatsapp.client import WhatsAppClient
  from apps.core.services.response_builder import ResponseBuilder

  logger = logging.getLogger(__name__)

  @shared_task(
      bind=True,
      max_retries=3,
      default_retry_delay=30,
      autoretry_for=(Exception,),
      retry_backoff=True
  )
  def emitir_nfe_task(self, nota_fiscal_id: str):
      """
      Task assíncrona para emitir NFSe.
      """
      logger.info(
          f'Emitindo NFSe - Tentativa {self.request.retries + 1}',
          extra={
              'nota_fiscal_id': nota_fiscal_id,
              'task_id': self.request.id
          }
      )

      try:
          # Emitir nota
          emitter = NFeEmitter()
          result = emitter.emitir(nota_fiscal_id)

          # Buscar nota atualizada
          nota = NotaFiscal.objects.select_related(
              'cliente_contabilidade'
          ).get(id=nota_fiscal_id)

          # Enviar WhatsApp
          whatsapp_client = WhatsAppClient()
          response_builder = ResponseBuilder()

          if result['sucesso']:
              # Sucesso - enviar PDF
              mensagem = response_builder.build_nota_aprovada(nota.numero_nfe)
              whatsapp_client.send_message(
                  nota.cliente_contabilidade.telefone,
                  mensagem
              )

              # Enviar PDF como documento
              # TODO: Implementar envio de arquivo
              logger.info(f'PDF da nota {nota.numero_nfe} enviado')

              # Salvar no histórico para IA (futuro)
              # TODO: Implementar

          else:
              # Erro - notificar cliente
              mensagem = response_builder.build_nota_erro(result['erro'])
              whatsapp_client.send_message(
                  nota.cliente_contabilidade.telefone,
                  mensagem
              )

          logger.info('Task de emissão concluída')
          return result

      except Exception as exc:
          logger.exception('Erro na task de emissão')

          # Marcar nota como erro
          try:
              nota = NotaFiscal.objects.get(id=nota_fiscal_id)
              nota.status = StatusNotaFiscalChoices.ERRO
              nota.error_message = str(exc)
              nota.save()
          except:
              pass

          # Retry
          raise
  ```

### 8.6 Integrar com Message Processor

- [ ] **8.6.1** Atualizar `MessageProcessor._handle_confirmacao()` em `apps/core/services/message_processor.py`
  ```python
  def _handle_confirmacao(self, telefone: str, mensagem: str, cliente, estado) -> str:
      """Processa confirmação do cliente."""
      from apps.nfe.models import NotaFiscal
      from apps.nfe.tasks import emitir_nfe_task
      from decimal import Decimal

      mensagem_lower = mensagem.lower().strip()

      if mensagem_lower in ['sim', 's', 'ok', 'confirmo', 'confirmar']:
          # Recuperar dados
          dados = estado['dados']
          protocolo_id = estado['protocolo_id']

          # Buscar protocolo
          from apps.core.models import Protocolo, EstadoMensagemChoices
          protocolo = Protocolo.objects.get(id=protocolo_id)

          # Criar nota fiscal
          nota = NotaFiscal.objects.create(
              contabilidade=cliente.contabilidade,
              cliente_contabilidade=cliente,
              protocolo=protocolo,
              cnpj_tomador=dados.get('cnpj_tomador'),
              razao_social_tomador=dados.get('razao_social_tomador', dados.get('tomador')),
              valor=Decimal(str(dados.get('valor'))),
              descricao=dados.get('descricao'),
              codigo_servico_municipal=dados.get('codigo_servico') or cliente.codigo_servico_municipal_padrao,
              aliquota_iss=cliente.aliquota_iss,
              valor_iss=Decimal(str(dados.get('valor'))) * cliente.aliquota_iss
          )

          # Atualizar protocolo
          protocolo.estado_mensagem = EstadoMensagemChoices.CONFIRMADO
          protocolo.save()

          # Disparar task assíncrona
          emitir_nfe_task.delay(str(nota.id))

          # Limpar estado
          self.state_manager.clear_state(telefone)

          return self.response_builder.build_confirmacao_processando(
              protocolo.numero_protocolo
          )

      elif mensagem_lower in ['não', 'nao', 'n', 'cancelar']:
          return self._handle_cancel(telefone)
      else:
          return 'Por favor, responda SIM para confirmar ou NÃO para cancelar.'
  ```

### 8.7 Configurações Adicionais

- [ ] **8.7.1** Adicionar ao `settings.py`
  ```python
  # Tecnospeed
  USE_FAKE_TECNOSPEED = config('USE_FAKE_TECNOSPEED', default=True, cast=bool)
  TECNOSPEED_WSDL_URL = config('TECNOSPEED_WSDL_URL', default='')
  ```

### 8.8 Testes Integrados

- [ ] **8.8.1** Testar criação manual de nota no admin

- [ ] **8.8.2** Testar emissão via shell
  ```python
  from apps.nfe.services.nfe_emitter import NFeEmitter
  from apps.nfe.models import NotaFiscal

  # Criar nota de teste
  nota = NotaFiscal.objects.first()

  # Emitir
  emitter = NFeEmitter()
  result = emitter.emitir(str(nota.id))
  print(result)
  ```

- [ ] **8.8.3** Testar task Celery
  ```python
  from apps.nfe.tasks import emitir_nfe_task

  nota = NotaFiscal.objects.first()
  task = emitir_nfe_task.delay(str(nota.id))
  print(f'Task ID: {task.id}')
  ```

- [ ] **8.8.4** Testar fluxo completo via WhatsApp webhook

---

## SPRINT 9: Frontend Dashboard e Templates

**Objetivo:** Criar interfaces web completas e design system
**Duração estimada:** 5-6 dias

### 9.1 Base Template e Design System

- [ ] **9.1.1** Criar `templates/base.html` completo
  ```html
  {% load static %}
  <!DOCTYPE html>
  <html lang="pt-BR">
  <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>{% block title %}AgentBase NFe{% endblock %}</title>

      <!-- Bootstrap 5 -->
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
      <!-- Bootstrap Icons -->
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
      <!-- Custom CSS -->
      <link rel="stylesheet" href="{% static 'css/custom.css' %}">

      {% block extra_css %}{% endblock %}
  </head>
  <body class="bg-dark text-light">
      <!-- Navbar -->
      {% if user.is_authenticated %}
      {% include 'components/navbar.html' %}
      {% endif %}

      <!-- Main Container -->
      <div class="container-fluid">
          <div class="row">
              <!-- Sidebar -->
              {% if user.is_authenticated %}
              <div class="col-md-2 d-none d-md-block bg-gradient-dark vh-100 sticky-top">
                  {% include 'components/sidebar.html' %}
              </div>
              <div class="col-md-10">
              {% else %}
              <div class="col-12">
              {% endif %}
                  <!-- Messages -->
                  {% if messages %}
                  <div class="mt-3">
                      {% for message in messages %}
                      <div class="alert alert-{{ message.tags }} alert-dismissible fade show">
                          {{ message }}
                          <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                      </div>
                      {% endfor %}
                  </div>
                  {% endif %}

                  <!-- Content -->
                  <main class="py-4">
                      {% block content %}{% endblock %}
                  </main>
              </div>
          </div>
      </div>

      <!-- Footer -->
      <footer class="footer mt-auto py-3 bg-gradient-dark">
          <div class="container text-center text-muted">
              <span>&copy; 2025 AgentBase NFe. Todos os direitos reservados.</span>
          </div>
      </footer>

      <!-- Bootstrap JS -->
      <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
      <!-- Custom JS -->
      <script src="{% static 'js/main.js' %}"></script>

      {% block extra_js %}{% endblock %}
  </body>
  </html>
  ```

- [ ] **9.1.2** Criar `static/css/custom.css`
  ```css
  :root {
      /* Cores */
      --primary: #667eea;
      --secondary: #764ba2;
      --success: #48bb78;
      --danger: #f56565;
      --warning: #ed8936;
      --info: #4299e1;

      /* Background */
      --dark: #1a202c;
      --dark-secondary: #2d3748;
      --dark-tertiary: #4a5568;

      /* Text */
      --text-primary: #f7fafc;
      --text-secondary: #e2e8f0;
      --text-muted: #a0aec0;
  }

  /* Gradientes */
  .bg-gradient-primary {
      background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
  }

  .bg-gradient-dark {
      background: linear-gradient(180deg, var(--dark) 0%, var(--dark-secondary) 100%);
  }

  .btn-gradient-primary {
      background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
      border: none;
      color: white;
  }

  .btn-gradient-primary:hover {
      background: linear-gradient(135deg, #5568d3 0%, #653a8b 100%);
      color: white;
  }

  /* Cards */
  .card {
      background: var(--dark-secondary);
      border: 1px solid var(--dark-tertiary);
  }

  .card-header {
      background: var(--dark);
      border-bottom: 1px solid var(--dark-tertiary);
  }

  /* Tables */
  .table-dark {
      --bs-table-bg: var(--dark-secondary);
      --bs-table-hover-bg: var(--dark-tertiary);
  }

  /* Forms */
  .form-control, .form-select {
      background: var(--dark);
      border-color: var(--dark-tertiary);
      color: var(--text-primary);
  }

  .form-control:focus, .form-select:focus {
      background: var(--dark);
      border-color: var(--primary);
      color: var(--text-primary);
      box-shadow: 0 0 0 0.25rem rgba(102, 126, 234, 0.25);
  }

  /* Badges */
  .badge {
      padding: 0.5em 1em;
  }

  /* Stats Cards */
  .stat-card {
      background: var(--dark-secondary);
      border-left: 4px solid var(--primary);
      padding: 1.5rem;
      border-radius: 0.5rem;
  }

  .stat-card .icon {
      font-size: 2.5rem;
      color: var(--primary);
  }

  .stat-card .number {
      font-size: 2rem;
      font-weight: bold;
  }

  /* Sidebar */
  .sidebar-link {
      color: var(--text-secondary);
      text-decoration: none;
      padding: 0.75rem 1rem;
      display: block;
      border-radius: 0.25rem;
      transition: all 0.3s;
  }

  .sidebar-link:hover {
      background: var(--dark-secondary);
      color: var(--primary);
  }

  .sidebar-link.active {
      background: var(--dark-secondary);
      color: var(--primary);
      border-left: 3px solid var(--primary);
  }
  ```

### 9.2 Components

- [ ] **9.2.1** Criar `templates/components/navbar.html`
- [ ] **9.2.2** Criar `templates/components/sidebar.html`
- [ ] **9.2.3** Criar `templates/components/pagination.html`
- [ ] **9.2.4** Criar `templates/components/card_stat.html`

### 9.3 Dashboard Principal

- [ ] **9.3.1** Implementar `DashboardView` completa
- [ ] **9.3.2** Criar template `templates/contabilidade/dashboard.html`
- [ ] **9.3.3** Adicionar cards de estatísticas
- [ ] **9.3.4** Adicionar gráficos (Chart.js)
- [ ] **9.3.5** Adicionar tabela de últimas notas

### 9.4 CRUD de Clientes

- [ ] **9.4.1** Template `cliente_list.html` completo
- [ ] **9.4.2** Template `cliente_form.html` completo
- [ ] **9.4.3** Template `cliente_detail.html` completo
- [ ] **9.4.4** Implementar busca e filtros
- [ ] **9.4.5** Implementar paginação

### 9.5 Lista de Notas Fiscais

- [ ] **9.5.1** Criar `NotaFiscalListView`
- [ ] **9.5.2** Template `nota_list.html`
- [ ] **9.5.3** Template `nota_detail.html`
- [ ] **9.5.4** Filtros por status, data, cliente
- [ ] **9.5.5** Export para CSV/Excel

### 9.6 Homepage Pública

- [ ] **9.6.1** Criar `HomeView` para página inicial
- [ ] **9.6.2** Template `home.html` apresentação
- [ ] **9.6.3** Seção de features
- [ ] **9.6.4** Seção de preços/planos
- [ ] **9.6.5** Call to action (Login/Cadastre-se)

### 9.7 Responsividade

- [ ] **9.7.1** Testar em mobile (375px)
- [ ] **9.7.2** Testar em tablet (768px)
- [ ] **9.7.3** Testar em desktop (1920px)
- [ ] **9.7.4** Ajustar sidebar mobile
- [ ] **9.7.5** Ajustar tabelas mobile

---

## SPRINT 10: Fluxos Completos e Refinamentos

**Objetivo:** Completar fluxos end-to-end e polish
**Duração estimada:** 4-5 dias

### 10.1 Fluxo de Emissão Completo

- [ ] **10.1.1** Testar fluxo: mensagem → extração → confirmação → emissão
- [ ] **10.1.2** Testar fluxo de dados incompletos
- [ ] **10.1.3** Testar fluxo de cancelamento
- [ ] **10.1.4** Testar retry logic
- [ ] **10.1.5** Testar timeout/expiração

### 10.2 Cleanup Task Periódica

- [ ] **10.2.1** Implementar task de limpeza de estados expirados
  ```python
  from celery import shared_task
  from celery.schedules import crontab

  @shared_task
  def cleanup_expired_states():
      # Implementar limpeza de estados no Redis
      pass
  ```

- [ ] **10.2.2** Configurar Celery Beat schedule

### 10.3 Notificações e Emails

- [ ] **10.3.1** Configurar SMTP no `settings.py`
- [ ] **10.3.2** Criar template de email para NFe
- [ ] **10.3.3** Task de envio de email
- [ ] **10.3.4** Anexar PDF ao email

### 10.4 Histórico e Auditoria

- [ ] **10.4.1** Salvar dados no histórico após emissão
- [ ] **10.4.2** Implementar busca semântica real (embeddings)
- [ ] **10.4.3** Criar view de histórico de protocolos
- [ ] **10.4.4** Criar view de auditoria

### 10.5 Validações e Error Handling

- [ ] **10.5.1** Validar CNPJ completo (dígitos verificadores)
- [ ] **10.5.2** Validar limites do plano
- [ ] **10.5.3** Tratar erros de gateway com mensagens amigáveis
- [ ] **10.5.4** Implementar rate limiting

### 10.6 Performance

- [ ] **10.6.1** Adicionar índices faltantes
- [ ] **10.6.2** Otimizar queries N+1
- [ ] **10.6.3** Implementar cache de queries frequentes
- [ ] **10.6.4** Configurar connection pooling

### 10.7 Documentação

- [ ] **10.7.1** Atualizar README.md
- [ ] **10.7.2** Documentar variáveis de ambiente
- [ ] **10.7.3** Documentar comandos principais
- [ ] **10.7.4** Criar guia de desenvolvimento

---

## SPRINT 11: Testes Automatizados

**Objetivo:** Implementar testes unitários e integração
**Duração estimada:** 4-5 dias

### 11.1 Setup de Testes

- [ ] **11.1.1** Instalar pytest e dependências
  ```bash
  pip install pytest pytest-django pytest-cov factory-boy
  ```

- [ ] **11.1.2** Criar `pytest.ini`
- [ ] **11.1.3** Criar estrutura `tests/`
- [ ] **11.1.4** Criar factories com factory_boy

### 11.2 Testes de Models

- [ ] **11.2.1** Testes de `Contabilidade`
- [ ] **11.2.2** Testes de `ClienteContabilidade`
- [ ] **11.2.3** Testes de `Protocolo`
- [ ] **11.2.4** Testes de `NotaFiscal`
- [ ] **11.2.5** Testes de `CertificadoDigital`

### 11.3 Testes de Services

- [ ] **11.3.1** Testes de `StateManager`
- [ ] **11.3.2** Testes de `AIExtractor`
- [ ] **11.3.3** Testes de `AIValidator`
- [ ] **11.3.4** Testes de `MessageProcessor`
- [ ] **11.3.5** Testes de `NFeEmitter`

### 11.4 Testes de Views

- [ ] **11.4.1** Testes de `LoginView`
- [ ] **11.4.2** Testes de `DashboardView`
- [ ] **11.4.3** Testes de CRUD de Clientes
- [ ] **11.4.4** Testes de `WhatsAppWebhookView`

### 11.5 Testes de Integração

- [ ] **11.5.1** Teste de fluxo completo de emissão
- [ ] **11.5.2** Teste de webhook → task → resposta
- [ ] **11.5.3** Teste de multi-tenant isolation

### 11.6 Coverage

- [ ] **11.6.1** Gerar relatório de coverage
- [ ] **11.6.2** Atingir >80% de coverage
- [ ] **11.6.3** Documentar áreas não cobertas

---

## SPRINT 12: Docker e Deploy

**Objetivo:** Containerizar aplicação e preparar deploy
**Duração estimada:** 3-4 dias

### 12.1 Docker

- [ ] **12.1.1** Criar `Dockerfile`
- [ ] **12.1.2** Criar `docker-compose.yml`
- [ ] **12.1.3** Criar `.dockerignore`
- [ ] **12.1.4** Build e teste local

### 12.2 Nginx

- [ ] **12.2.1** Configurar Nginx como reverse proxy
- [ ] **12.2.2** Configurar SSL/HTTPS
- [ ] **12.2.3** Configurar static files

### 12.3 Environment

- [ ] **12.3.1** Criar `requirements/production.txt`
- [ ] **12.3.2** Configurar variáveis de produção
- [ ] **12.3.3** Configurar secrets management

### 12.4 CI/CD

- [ ] **12.4.1** Configurar GitHub Actions
- [ ] **12.4.2** Pipeline de testes
- [ ] **12.4.3** Pipeline de deploy
- [ ] **12.4.4** Configurar ambientes (staging/production)

### 12.5 Monitoramento

- [ ] **12.5.1** Configurar Sentry (error tracking)
- [ ] **12.5.2** Configurar logs centralizados
- [ ] **12.5.3** Configurar métricas (Prometheus)
- [ ] **12.5.4** Criar dashboards (Grafana)

### 12.6 Backup e Recovery

- [ ] **12.6.1** Script de backup PostgreSQL
- [ ] **12.6.2** Script de backup Redis
- [ ] **12.6.3** Testar restore
- [ ] **12.6.4** Automatizar backups

### 12.7 Documentação Final

- [ ] **12.7.1** Guia de deploy
- [ ] **12.7.2** Guia de troubleshooting
- [ ] **12.7.3** Documentação de API
- [ ] **12.7.4** Changelog

---

## OBSERVAÇÕES FINAIS

### Priorização
- Sprints 1-6: **CRÍTICO** - Base do sistema
- Sprints 7-8: **ALTO** - Funcionalidade core
- Sprint 9: **MÉDIO** - UI/UX
- Sprint 10: **ALTO** - Refinamentos essenciais
- Sprint 11: **MÉDIO** - Qualidade
- Sprint 12: **ALTO** - Deploy

### Dependências
- Sprint 2 depende de Sprint 1
- Sprint 3 depende de Sprint 2
- Sprint 4-6 podem ter algum paralelismo
- Sprint 7-8 dependem de Sprint 6
- Sprint 9 pode ser paralelo a Sprint 8
- Sprint 10 depende de todos anteriores
- Sprint 11-12 são finais

### Estimativa Total
- **Desenvolvimento**: 40-55 dias úteis
- **Com imprevistos**: 50-65 dias úteis
- **Em sprints de 2 semanas**: ~6-7 sprints

---

**FIM DO PLANO DE DESENVOLVIMENTO**
