from django.db import models


class Contabilidade(models.Model):
    '''
    Empresa de contabilidade (tenant).
    Cada contabilidade é isolada e tem suas próprias empresas e usuários.
    '''
    cnpj = models.CharField('CNPJ', max_length=18, unique=True)
    razao_social = models.CharField('razão social', max_length=200)
    nome_fantasia = models.CharField('nome fantasia', max_length=200, blank=True)

    # Contato
    email = models.EmailField('e-mail')
    telefone_ddd = models.CharField('DDD', max_length=2, blank=True)
    telefone_numero = models.CharField('telefone', max_length=15, blank=True)

    # Endereço
    cep = models.CharField('CEP', max_length=9, blank=True)
    logradouro = models.CharField('logradouro', max_length=200, blank=True)
    numero = models.CharField('número', max_length=20, blank=True)
    complemento = models.CharField('complemento', max_length=100, blank=True)
    bairro = models.CharField('bairro', max_length=100, blank=True)
    cidade = models.CharField('cidade', max_length=100, blank=True)
    estado = models.CharField('estado', max_length=2, blank=True)

    # Status
    is_active = models.BooleanField('ativo', default=True)
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'contabilidade'
        verbose_name_plural = 'contabilidades'
        ordering = ['razao_social']

    def __str__(self):
        return self.nome_fantasia or self.razao_social


class Empresa(models.Model):
    '''
    Empresa cliente da contabilidade.
    Compatível com a estrutura da API Tecnospeed.
    '''
    contabilidade = models.ForeignKey(
        Contabilidade,
        on_delete=models.CASCADE,
        related_name='empresas',
        verbose_name='contabilidade'
    )

    # Dados Básicos (compatível com Tecnospeed)
    cpf_cnpj = models.CharField('CPF/CNPJ', max_length=18)
    razao_social = models.CharField('razão social', max_length=200)
    nome_fantasia = models.CharField('nome fantasia', max_length=200, blank=True)
    inscricao_municipal = models.CharField('inscrição municipal', max_length=20, blank=True)
    inscricao_estadual = models.CharField('inscrição estadual', max_length=20, blank=True)

    # Regime Tributário
    simples_nacional = models.BooleanField('Simples Nacional', default=False)
    REGIME_CHOICES = [
        (1, 'Simples Nacional'),
        (2, 'Simples Nacional - Excesso'),
        (3, 'Regime Normal'),
    ]
    regime_tributario = models.IntegerField(
        'regime tributário',
        choices=REGIME_CHOICES,
        default=3
    )
    incentivo_fiscal = models.BooleanField('incentivo fiscal', default=False)
    incentivador_cultural = models.BooleanField('incentivador cultural', default=False)
    REGIME_ESPECIAL_CHOICES = [
        (0, 'Nenhum'),
        (1, 'Microempresa Municipal'),
        (2, 'Estimativa'),
        (3, 'Sociedade de Profissionais'),
        (4, 'Cooperativa'),
        (5, 'MEI'),
        (6, 'ME/EPP'),
    ]
    regime_tributario_especial = models.IntegerField(
        'regime tributário especial',
        choices=REGIME_ESPECIAL_CHOICES,
        default=0
    )

    # Endereço
    cep = models.CharField('CEP', max_length=9, blank=True)
    logradouro = models.CharField('logradouro', max_length=200, blank=True)
    numero = models.CharField('número', max_length=20, blank=True)
    complemento = models.CharField('complemento', max_length=100, blank=True)
    bairro = models.CharField('bairro', max_length=100, blank=True)
    tipo_logradouro = models.CharField('tipo logradouro', max_length=50, blank=True)
    tipo_bairro = models.CharField('tipo bairro', max_length=50, blank=True)
    codigo_cidade = models.CharField('código cidade (IBGE)', max_length=7, blank=True)
    descricao_cidade = models.CharField('cidade', max_length=100, blank=True)
    estado = models.CharField('estado', max_length=2, blank=True)
    codigo_pais = models.CharField('código país', max_length=4, default='1058')
    descricao_pais = models.CharField('país', max_length=100, default='Brasil')

    # Contato
    telefone_ddd = models.CharField('DDD', max_length=2, blank=True)
    telefone_numero = models.CharField('telefone', max_length=15, blank=True)
    email = models.EmailField('e-mail', blank=True)

    # NFSe Config
    nfse_ativo = models.BooleanField('NFSe ativo', default=True)
    nfse_producao = models.BooleanField('ambiente produção', default=False)

    # Tecnospeed
    tecnospeed_id = models.CharField(
        'ID empresa Tecnospeed',
        max_length=50,
        blank=True,
        help_text='ID retornado pela API Tecnospeed ao cadastrar empresa'
    )

    # Status
    is_active = models.BooleanField('ativo', default=True)
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'empresa'
        verbose_name_plural = 'empresas'
        ordering = ['razao_social']
        unique_together = ['contabilidade', 'cpf_cnpj']
        indexes = [
            models.Index(fields=['contabilidade', 'cpf_cnpj']),
            models.Index(fields=['contabilidade', 'is_active']),
        ]

    def __str__(self):
        return f'{self.razao_social} ({self.cpf_cnpj})' 


class UsuarioEmpresa(models.Model):
    '''
    Pessoa física autorizada a solicitar emissão de notas para uma Empresa.
    São os usuários que interagem via WhatsApp.
    '''
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='usuarios_autorizados',
        verbose_name='empresa'
    )

    nome = models.CharField('nome', max_length=200)
    cpf = models.CharField('CPF', max_length=14, blank=True)
    telefone = models.CharField('telefone (WhatsApp)', max_length=20)
    email = models.EmailField('e-mail', blank=True)

    # Endereço (opcional)
    cep = models.CharField('CEP', max_length=9, blank=True)
    logradouro = models.CharField('logradouro', max_length=200, blank=True)
    numero = models.CharField('número', max_length=20, blank=True)
    complemento = models.CharField('complemento', max_length=100, blank=True)
    bairro = models.CharField('bairro', max_length=100, blank=True)
    cidade = models.CharField('cidade', max_length=100, blank=True)
    estado = models.CharField('estado', max_length=2, blank=True)

    is_active = models.BooleanField('ativo', default=True)
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'usuário da empresa'
        verbose_name_plural = 'usuários da empresa'
        ordering = ['nome']
        constraints = [
            models.UniqueConstraint(
                fields=['telefone'],
                condition=models.Q(is_active=True),
                name='unique_telefone_ativo',
                violation_error_message='Este telefone já está cadastrado em outra empresa ativa.'
            )
        ]

    def __str__(self):
        return f'{self.nome} - {self.telefone}'


class Certificado(models.Model):
    '''
    Certificado digital para assinatura de NFSe.
    Pertence a uma Empresa (cliente da contabilidade).
    '''
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='certificados',
        verbose_name='empresa'
    )

    arquivo = models.FileField(
        'arquivo (.pfx)',
        upload_to='certificados/',
        help_text='Arquivo do certificado digital no formato .pfx'
    )
    senha = models.CharField(
        'senha',
        max_length=100,
        help_text='Senha do certificado (armazenada de forma segura)'
    )

    # Dados extraídos do certificado
    nome_titular = models.CharField('nome titular', max_length=200, blank=True)
    cnpj_titular = models.CharField('CNPJ titular', max_length=18, blank=True)
    validade = models.DateField('data validade', null=True, blank=True)

    # Integração Tecnospeed
    tecnospeed_id = models.CharField(
        'ID Tecnospeed',
        max_length=50,
        blank=True,
        help_text='ID retornado ao enviar para Tecnospeed'
    )
    enviado_tecnospeed = models.BooleanField('enviado para Tecnospeed', default=False)
    data_envio_tecnospeed = models.DateTimeField(
        'data envio Tecnospeed',
        null=True,
        blank=True
    )

    is_active = models.BooleanField('ativo', default=True)
    created_at = models.DateTimeField('criado em', auto_now_add=True)
    updated_at = models.DateTimeField('atualizado em', auto_now=True)

    class Meta:
        verbose_name = 'certificado digital'
        verbose_name_plural = 'certificados digitais'
        ordering = ['-created_at']

    def __str__(self):
        return f'Certificado {self.empresa.razao_social} - {self.validade}'

    @property
    def is_valid(self):
        '''Verifica se o certificado está dentro da validade.'''
        from django.utils import timezone
        if not self.validade:
            return False
        return self.validade >= timezone.now().date()

    @property
    def days_to_expire(self):
        '''Dias até a expiração do certificado.'''
        from django.utils import timezone
        if not self.validade:
            return None
        delta = self.validade - timezone.now().date()
        return delta.days
