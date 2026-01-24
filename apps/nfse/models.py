from django.db import models
import logging

logger = logging.getLogger(__name__)


class ClienteTomador(models.Model):
    """Dados do tomador de serviços (cliente) obtidos da Receita Federal."""
    
    # Identificação
    cnpj = models.CharField(max_length=14, unique=True, db_index=True, verbose_name='CNPJ')
    razao_social = models.CharField(max_length=255, verbose_name='Razão Social')
    nome_fantasia = models.CharField(max_length=255, blank=True, verbose_name='Nome Fantasia')
    
    # Contato
    email = models.EmailField(blank=True, verbose_name='E-mail')
    telefone = models.CharField(max_length=20, blank=True, verbose_name='Telefone')
    
    # Inscrições
    inscricao_municipal = models.CharField(max_length=20, blank=True, verbose_name='Inscrição Municipal')
    inscricao_estadual = models.CharField(max_length=20, blank=True, verbose_name='Inscrição Estadual')
    
    # Endereço
    cep = models.CharField(max_length=8, verbose_name='CEP')
    logradouro = models.CharField(max_length=255, verbose_name='Logradouro')
    numero = models.CharField(max_length=10, verbose_name='Número')
    complemento = models.CharField(max_length=100, blank=True, verbose_name='Complemento')
    bairro = models.CharField(max_length=100, verbose_name='Bairro')
    cidade = models.CharField(max_length=100, verbose_name='Cidade')
    codigo_cidade = models.CharField(max_length=7, verbose_name='Código IBGE')
    estado = models.CharField(max_length=2, verbose_name='UF')
    
    # Metadados
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    
    # Dados brutos da API (para auditoria)
    dados_receita_raw = models.JSONField(blank=True, null=True, verbose_name='Dados Brutos Receita')
    
    class Meta:
        verbose_name = 'Cliente Tomador'
        verbose_name_plural = 'Clientes Tomadores'
        ordering = ['razao_social']
    
    def __str__(self):
        return f"{self.cnpj} - {self.razao_social}"


class NFSeEmissao(models.Model):
    """Registro de emissão de NFSe (antes do envio)."""
    
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('enviado', 'Enviado'),
        ('processando', 'Processando'),
        ('concluido', 'Concluído'),
        ('erro', 'Erro'),
        ('cancelado', 'Cancelado'),
    ]
    
    # Relacionamentos
    session = models.ForeignKey(
        'core.SessionSnapshot',
        on_delete=models.CASCADE,
        related_name='nfse_emissoes',
        verbose_name='Sessão'
    )
    prestador = models.ForeignKey(
        'contabilidade.Empresa',
        on_delete=models.PROTECT,
        related_name='nfse_emitidas',
        verbose_name='Prestador'
    )
    tomador = models.ForeignKey(
        'ClienteTomador',
        on_delete=models.PROTECT,
        related_name='nfse_recebidas',
        verbose_name='Tomador'
    )
    
    # Controle
    id_integracao = models.CharField(max_length=50, unique=True, db_index=True, verbose_name='ID Integração')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente', verbose_name='Status')
    
    # Dados do serviço
    codigo_servico = models.CharField(max_length=10, default='14.10', verbose_name='Código Serviço')
    codigo_tributacao = models.CharField(max_length=10, default='14.10', verbose_name='Código Tributação')
    descricao_servico = models.TextField(verbose_name='Descrição do Serviço')
    cnae = models.CharField(max_length=10, default='7490104', verbose_name='CNAE')
    
    # Valores
    valor_servico = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Valor do Serviço')
    desconto_condicionado = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Desconto Condicionado')
    desconto_incondicionado = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Desconto Incondicionado')
    
    # ISS
    tipo_tributacao = models.IntegerField(default=7, verbose_name='Tipo Tributação')
    exigibilidade = models.IntegerField(default=1, verbose_name='Exigibilidade')
    aliquota = models.DecimalField(max_digits=5, decimal_places=2, default=3, verbose_name='Alíquota ISS (%)')
    
    # JSON enviado/recebido
    payload_enviado = models.JSONField(blank=True, null=True, verbose_name='Payload Enviado')
    resposta_gateway = models.JSONField(blank=True, null=True, verbose_name='Resposta Gateway')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    enviado_em = models.DateTimeField(blank=True, null=True, verbose_name='Enviado em')
    processado_em = models.DateTimeField(blank=True, null=True, verbose_name='Processado em')
    
    # Mensagens de erro
    erro_mensagem = models.TextField(blank=True, verbose_name='Mensagem de Erro')
    
    class Meta:
        verbose_name = 'Emissão NFSe'
        verbose_name_plural = 'Emissões NFSe'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.id_integracao} - {self.get_status_display()}"


class NFSeProcessada(models.Model):
    """NFSe processada e autorizada (dados do webhook)."""
    
    # Relacionamento
    emissao = models.OneToOneField(
        'NFSeEmissao',
        on_delete=models.CASCADE,
        related_name='nota_processada',
        verbose_name='Emissão'
    )
    
    # Identificação da nota
    id_externo = models.CharField(max_length=50, unique=True, db_index=True, verbose_name='ID Externo')
    numero = models.CharField(max_length=20, verbose_name='Número')
    serie = models.CharField(max_length=10, blank=True, verbose_name='Série')
    chave = models.CharField(max_length=100, unique=True, verbose_name='Chave')
    protocolo = models.CharField(max_length=50, verbose_name='Protocolo')
    
    # Status e mensagem
    status = models.CharField(max_length=50, verbose_name='Status')
    mensagem = models.TextField(verbose_name='Mensagem')
    c_stat = models.IntegerField(verbose_name='Código Status Fiscal')
    
    # Dados fiscais
    emitente = models.CharField(max_length=14, verbose_name='CNPJ Emitente')
    destinatario = models.CharField(max_length=14, verbose_name='CNPJ/CPF Destinatário')
    valor = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Valor')
    
    # Datas
    data_emissao = models.DateField(verbose_name='Data Emissão')
    data_autorizacao = models.DateField(verbose_name='Data Autorização')
    
    # Arquivos
    url_xml = models.URLField(max_length=500, blank=True, verbose_name='URL XML')
    url_pdf = models.URLField(max_length=500, blank=True, verbose_name='URL PDF')
    
    # Metadados
    destinada = models.BooleanField(default=False, verbose_name='Destinada')
    documento = models.CharField(max_length=20, default='nfse', verbose_name='Tipo Documento')
    
    # Dados brutos
    webhook_payload = models.JSONField(verbose_name='Payload Webhook')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    
    class Meta:
        verbose_name = 'NFSe Processada'
        verbose_name_plural = 'NFSes Processadas'
        ordering = ['-data_emissao', '-numero']
    
    def __str__(self):
        return f"NFSe {self.numero} - {self.emitente}"
