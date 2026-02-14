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


class EmpresaClienteTomador(models.Model):
    """
    Relacionamento entre Empresa (prestadora) e ClienteTomador.
    Registra quando uma empresa trabalha com um cliente tomador.
    Evita duplicação de dados do cliente e permite rastreamento do relacionamento.
    """
    empresa = models.ForeignKey(
        'contabilidade.Empresa',
        on_delete=models.CASCADE,
        related_name='clientes_tomadores_vinculados',
        verbose_name='Empresa Prestadora'
    )
    cliente_tomador = models.ForeignKey(
        'ClienteTomador',
        on_delete=models.PROTECT,  # PROTECT: não permite deletar se tiver vínculos
        related_name='empresas_vinculadas',
        verbose_name='Cliente Tomador'
    )
    
    # Metadados do relacionamento
    primeira_nota_em = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Primeira Nota Emitida em',
        help_text='Data da primeira nota emitida pela empresa para este cliente'
    )
    ultima_nota_em = models.DateTimeField(
        auto_now=True,
        verbose_name='Última Nota Emitida em',
        help_text='Data da última nota emitida pela empresa para este cliente'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Relacionamento Ativo',
        help_text='Indica se a empresa ainda trabalha com este cliente'
    )
    
    # Campos opcionais para customização por empresa
    apelido = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Apelido do Cliente',
        help_text='Nome customizado que a empresa usa internamente para este cliente'
    )
    observacoes = models.TextField(
        blank=True,
        verbose_name='Observações Internas',
        help_text='Anotações da empresa sobre este cliente'
    )
    
    class Meta:
        verbose_name = 'Empresa-Cliente Tomador'
        verbose_name_plural = 'Empresas-Clientes Tomadores'
        unique_together = [['empresa', 'cliente_tomador']]
        indexes = [
            models.Index(fields=['empresa', 'cliente_tomador']),
            models.Index(fields=['empresa', 'is_active']),
            models.Index(fields=['-ultima_nota_em']),
        ]
        ordering = ['-ultima_nota_em']
    
    def __str__(self):
        if self.apelido:
            return f"{self.empresa.razao_social} → {self.apelido}"
        return f"{self.empresa.razao_social} → {self.cliente_tomador.razao_social}"
    
    # ==================== MÉTODOS DE AUDITORIA ====================
    
    def get_notas_emitidas(self):
        """
        Retorna QuerySet com todas as notas emitidas pela empresa para este cliente.
        Permite filtros adicionais, paginação, ordenação, etc.
        """
        return NFSeEmissao.objects.filter(
            prestador=self.empresa,
            tomador=self.cliente_tomador
        ).select_related('session', 'prestador', 'tomador')
    
    @property
    def total_notas(self):
        """Total de notas emitidas (calculado dinamicamente)."""
        return self.get_notas_emitidas().count()
    
    @property
    def total_valor_emitido(self):
        """Soma total dos valores de todas as notas emitidas."""
        from django.db.models import Sum
        resultado = self.get_notas_emitidas().aggregate(total=Sum('valor_servico'))
        return resultado['total'] or 0
    
    @property
    def ultima_nota(self):
        """Retorna a última nota emitida (ou None)."""
        return self.get_notas_emitidas().first()
    
    def notas_por_periodo(self, data_inicio, data_fim):
        """Retorna notas emitidas em um período específico."""
        return self.get_notas_emitidas().filter(
            created_at__range=[data_inicio, data_fim]
        )
    
    def notas_por_status(self, status):
        """Retorna notas filtradas por status."""
        return self.get_notas_emitidas().filter(status=status)
    
    def estatisticas(self):
        """Retorna dicionário com estatísticas completas do relacionamento."""
        from django.db.models import Count, Sum, Avg
        
        notas = self.get_notas_emitidas()
        stats = notas.aggregate(
            total_notas=Count('id'),
            valor_total=Sum('valor_servico'),
            valor_medio=Avg('valor_servico'),
        )
        
        # Notas por status
        stats['por_status'] = dict(
            notas.values('status').annotate(count=Count('id')).values_list('status', 'count')
        )
        
        # Primeira e última nota
        stats['primeira_nota_em'] = self.primeira_nota_em
        stats['ultima_nota_em'] = self.ultima_nota_em
        
        return stats


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
        indexes = [
            models.Index(fields=['prestador', '-created_at'], name='idx_emissao_prestador_data'),
            models.Index(fields=['prestador', 'tomador', '-created_at'], name='idx_emissao_prest_tom_data'),
        ]
    
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
