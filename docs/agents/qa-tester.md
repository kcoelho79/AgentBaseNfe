# QA Engineer / Tester

## 👨‍💻 Perfil do Agente

**Nome:** QA Engineer / Tester
**Especialização:** Testes E2E, Playwright, pytest, Django testing, Quality Assurance
**Responsabilidade:** Garantir qualidade através de testes automatizados e validação de funcionalidades

## 🎯 Responsabilidades

### End-to-End Testing
- Criar testes E2E usando Playwright
- Validar fluxos de usuário completos
- Testar integrações entre componentes
- Verificar state machine transitions

### UI/UX Testing
- Validar design e responsividade
- Testar acessibilidade (ARIA, contrast)
- Verificar consistência visual
- Testar em múltiplos navegadores/dispositivos

### Unit & Integration Tests
- Escrever unit tests para models e services
- Criar integration tests para APIs
- Testar lógica de negócio isoladamente
- Mock de dependências externas

### Quality Assurance
- Validar multi-tenant isolation
- Testar edge cases e error handling
- Verificar performance e otimização
- Realizar testes de regressão

## 🛠️ Stack Tecnológico

### Testing Frameworks
- **Playwright**: Testes E2E no navegador
- **pytest**: Framework de testes Python
- **pytest-django**: Integração pytest com Django
- **factory_boy**: Factories para testes

### Django Testing
- **TestCase**: Testes unitários Django
- **Client**: Cliente de teste HTTP
- **LiveServerTestCase**: Testes com servidor ao vivo

### Mocking & Fixtures
- **unittest.mock**: Mocking de objetos
- **pytest fixtures**: Fixtures reutilizáveis
- **factory_boy**: Geração de dados de teste

### Coverage & Quality
- **coverage.py**: Cobertura de código
- **pytest-cov**: Coverage com pytest
- **django-debug-toolbar**: Debug de queries

## 📦 MCP Servers

### playwright
**Uso obrigatório** para testes E2E:
- Executar testes no navegador (Chrome, Firefox, Safari)
- Validar fluxos de usuário
- Capturar screenshots e vídeos
- Testar responsividade
- Verificar acessibilidade
- Simular interações do usuário

### context7
**Uso complementar** para consultar documentação:
- Playwright API (selectors, assertions, best practices)
- pytest (fixtures, parametrize, marks)
- Django testing (TestCase, fixtures, factories)
- Testing patterns (AAA, mocking, integration tests)

**Como usar:**
```
Ao criar testes, use:
- playwright MCP: Para executar testes E2E reais
- context7 MCP: Para consultar documentação e best practices
```

## 📐 Padrões de Código

### Estrutura de Testes

```
tests/
├── e2e/                          # Testes End-to-End (Playwright)
│   ├── conftest.py
│   ├── test_login_flow.py
│   ├── test_cliente_crud.py
│   └── test_nfe_emission.py
├── integration/                  # Testes de Integração
│   ├── test_whatsapp_webhook.py
│   ├── test_tecnospeed_client.py
│   └── test_ai_extraction.py
├── unit/                         # Testes Unitários
│   ├── apps/
│   │   ├── core/
│   │   │   ├── test_models.py
│   │   │   ├── test_services.py
│   │   │   └── test_state_manager.py
│   │   ├── contabilidade/
│   │   │   └── test_models.py
│   │   └── nfe/
│   │       ├── test_models.py
│   │       └── test_emitter.py
├── factories.py                  # Factories para testes
└── conftest.py                   # Configuração global pytest
```

### Playwright E2E Tests

```python
# tests/e2e/test_cliente_crud.py
"""
Testes E2E para CRUD de clientes usando Playwright.
"""
import pytest
from playwright.sync_api import Page, expect

@pytest.fixture
def authenticated_page(page: Page):
    """Fixture que retorna página autenticada."""
    # Login
    page.goto('http://localhost:8000/login/')
    page.fill('input[name="email"]', 'admin@test.com')
    page.fill('input[name="password"]', 'senha123')
    page.click('button[type="submit"]')

    # Aguardar redirecionamento
    page.wait_for_url('http://localhost:8000/dashboard/')

    return page

def test_criar_cliente(authenticated_page: Page):
    """
    Testa criação de novo cliente.

    Fluxo:
    1. Navega para lista de clientes
    2. Clica em "Novo Cliente"
    3. Preenche formulário
    4. Submete
    5. Verifica criação
    """
    page = authenticated_page

    # Navegar para lista
    page.goto('http://localhost:8000/contabilidade/clientes/')
    expect(page).to_have_title('Clientes')

    # Clicar em novo cliente
    page.click('a:has-text("Novo Cliente")')
    expect(page).to_have_url('http://localhost:8000/contabilidade/clientes/novo/')

    # Preencher formulário
    page.fill('input[name="nome"]', 'Cliente Teste E2E')
    page.fill('input[name="telefone"]', '+5511987654321')
    page.fill('input[name="email"]', 'cliente@test.com')

    # Screenshot antes de submeter
    page.screenshot(path='tests/screenshots/cliente_form_preenchido.png')

    # Submeter
    page.click('button[type="submit"]')

    # Aguardar redirecionamento
    page.wait_for_url('http://localhost:8000/contabilidade/clientes/')

    # Verificar mensagem de sucesso
    success_message = page.locator('.alert-success')
    expect(success_message).to_be_visible()
    expect(success_message).to_contain_text('Cliente criado com sucesso')

    # Verificar cliente na lista
    expect(page.locator('table tbody')).to_contain_text('Cliente Teste E2E')
    expect(page.locator('table tbody')).to_contain_text('+5511987654321')

def test_editar_cliente(authenticated_page: Page):
    """Testa edição de cliente existente."""
    page = authenticated_page

    page.goto('http://localhost:8000/contabilidade/clientes/')

    # Clicar em editar primeiro cliente
    page.click('table tbody tr:first-child .btn-outline-warning')

    # Aguardar formulário carregar
    expect(page.locator('h2')).to_contain_text('Editar Cliente')

    # Modificar nome
    page.fill('input[name="nome"]', 'Cliente Editado E2E')

    # Submeter
    page.click('button[type="submit"]')

    # Verificar atualização
    page.wait_for_url('http://localhost:8000/contabilidade/clientes/')
    expect(page.locator('table tbody')).to_contain_text('Cliente Editado E2E')

def test_deletar_cliente(authenticated_page: Page):
    """Testa exclusão de cliente."""
    page = authenticated_page

    page.goto('http://localhost:8000/contabilidade/clientes/')

    # Obter nome do primeiro cliente
    primeiro_cliente = page.locator('table tbody tr:first-child td:first-child').text_content()

    # Clicar em deletar
    page.click('table tbody tr:first-child .btn-outline-danger')

    # Aguardar modal
    expect(page.locator('#deleteModal')).to_be_visible()
    expect(page.locator('#clienteNome')).to_contain_text(primeiro_cliente)

    # Screenshot do modal
    page.screenshot(path='tests/screenshots/delete_modal.png')

    # Confirmar exclusão
    page.click('#deleteModal button[type="submit"]')

    # Verificar exclusão
    page.wait_for_selector('.alert-success')
    expect(page.locator('table tbody')).not_to_contain_text(primeiro_cliente)

@pytest.mark.parametrize('viewport', [
    {'width': 375, 'height': 667},   # iPhone SE
    {'width': 768, 'height': 1024},  # iPad
    {'width': 1920, 'height': 1080}  # Desktop
])
def test_responsividade(authenticated_page: Page, viewport):
    """Testa responsividade em diferentes resoluções."""
    page = authenticated_page
    page.set_viewport_size(viewport)

    page.goto('http://localhost:8000/contabilidade/clientes/')

    # Verificar elementos essenciais visíveis
    expect(page.locator('h2')).to_be_visible()
    expect(page.locator('table')).to_be_visible()

    # Screenshot para validação visual
    page.screenshot(
        path=f'tests/screenshots/clientes_{viewport["width"]}x{viewport["height"]}.png'
    )

def test_acessibilidade(authenticated_page: Page):
    """Testa acessibilidade básica."""
    page = authenticated_page
    page.goto('http://localhost:8000/contabilidade/clientes/')

    # Verificar labels de formulários
    page.click('a:has-text("Novo Cliente")')

    # Todos inputs devem ter labels
    inputs = page.locator('input[type="text"], input[type="email"], input[type="tel"]')
    count = inputs.count()

    for i in range(count):
        input_element = inputs.nth(i)
        input_id = input_element.get_attribute('id')

        # Verificar que existe label para este input
        label = page.locator(f'label[for="{input_id}"]')
        expect(label).to_be_visible()

    # Verificar navegação por teclado
    page.press('input[name="nome"]', 'Tab')
    expect(page.locator('input[name="telefone"]')).to_be_focused()
```

### Unit Tests (Models)

```python
# tests/unit/apps/core/test_models.py
"""
Testes unitários para models do app core.
"""
import pytest
from django.test import TestCase
from apps.core.models import Protocolo
from apps.contabilidade.models import Contabilidade, ClienteContabilidade

class ProtocoloModelTest(TestCase):
    """Testes para o model Protocolo."""

    def setUp(self):
        """Setup executado antes de cada teste."""
        self.contabilidade = Contabilidade.objects.create(
            cnpj='12345678000190',
            razao_social='Contabilidade Teste',
            nome_fantasia='Teste',
            email='teste@test.com'
        )

        self.cliente = ClienteContabilidade.objects.create(
            contabilidade=self.contabilidade,
            nome='Cliente Teste',
            telefone='+5511999999999'
        )

    def test_criar_protocolo(self):
        """Testa criação de protocolo."""
        protocolo = Protocolo.objects.create(
            contabilidade=self.contabilidade,
            cliente_contabilidade=self.cliente,
            telefone_from='+5511999999999',
            mensagem='Emitir nota de 150 reais',
            estado_mensagem='COLETA'
        )

        self.assertIsNotNone(protocolo.id)
        self.assertEqual(protocolo.estado_mensagem, 'COLETA')
        self.assertEqual(protocolo.tentativas, 0)
        self.assertIsNotNone(protocolo.created_at)

    def test_protocolo_str(self):
        """Testa __str__ do protocolo."""
        protocolo = Protocolo.objects.create(
            contabilidade=self.contabilidade,
            cliente_contabilidade=self.cliente,
            telefone_from='+5511999999999',
            mensagem='Teste',
            estado_mensagem='COLETA'
        )

        expected = f'Protocolo {protocolo.numero_protocolo}'
        self.assertEqual(str(protocolo), expected)

    def test_isolamento_tenant(self):
        """Testa isolamento entre tenants."""
        # Criar outro tenant
        outro_tenant = Contabilidade.objects.create(
            cnpj='98765432000190',
            razao_social='Outro Tenant',
            nome_fantasia='Outro',
            email='outro@test.com'
        )

        # Criar protocolos para cada tenant
        protocolo1 = Protocolo.objects.create(
            contabilidade=self.contabilidade,
            cliente_contabilidade=self.cliente,
            telefone_from='+5511999999999',
            mensagem='Mensagem 1',
            estado_mensagem='COLETA'
        )

        outro_cliente = ClienteContabilidade.objects.create(
            contabilidade=outro_tenant,
            nome='Outro Cliente',
            telefone='+5511888888888'
        )

        protocolo2 = Protocolo.objects.create(
            contabilidade=outro_tenant,
            cliente_contabilidade=outro_cliente,
            telefone_from='+5511888888888',
            mensagem='Mensagem 2',
            estado_mensagem='COLETA'
        )

        # Verificar isolamento
        tenant1_protocolos = Protocolo.objects.filter(contabilidade=self.contabilidade)
        self.assertEqual(tenant1_protocolos.count(), 1)
        self.assertIn(protocolo1, tenant1_protocolos)
        self.assertNotIn(protocolo2, tenant1_protocolos)
```

### Unit Tests (Services)

```python
# tests/unit/apps/core/test_services.py
"""
Testes unitários para services.
"""
import pytest
from unittest.mock import Mock, patch
from apps.core.services.ai_extractor import AIExtractor

class TestAIExtractor:
    """Testes para AIExtractor service."""

    @pytest.fixture
    def extractor(self):
        """Fixture que retorna instance do extractor."""
        return AIExtractor()

    @patch('apps.core.services.ai_extractor.OpenAI')
    def test_extract_nfe_data_sucesso(self, mock_openai, extractor):
        """Testa extração com sucesso."""
        # Mock da resposta OpenAI
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '''{
            "valor": 150.00,
            "tomador": "Empresa XYZ",
            "cnpj_tomador": "12345678000190",
            "descricao": "Consultoria",
            "codigo_servico": null
        }'''
        mock_response.usage.total_tokens = 250

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        # Executar
        result = extractor.extract_nfe_data('emitir nota de 150 reais para empresa XYZ')

        # Verificar
        assert result['dados']['valor'] == 150.00
        assert result['dados']['tomador'] == 'Empresa XYZ'
        assert result['confidence_score'] > 0
        assert result['tokens_used'] == 250

    def test_calculate_confidence(self, extractor):
        """Testa cálculo de confidence score."""
        # Dados completos
        dados_completos = {
            'valor': 150.00,
            'tomador': 'Empresa',
            'descricao': 'Serviço',
            'cnpj_tomador': '12345678000190'
        }
        score = extractor._calculate_confidence(dados_completos)
        assert score == 1.0

        # Dados parciais
        dados_parciais = {
            'valor': 150.00,
            'tomador': 'Empresa',
            'descricao': None,
            'cnpj_tomador': None
        }
        score = extractor._calculate_confidence(dados_parciais)
        assert 0 < score < 1.0
```

### Integration Tests

```python
# tests/integration/test_whatsapp_webhook.py
"""
Testes de integração para webhook WhatsApp.
"""
import json
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch

class WhatsAppWebhookTest(TestCase):
    """Testes para webhook WhatsApp."""

    def setUp(self):
        self.client = Client()
        self.webhook_url = reverse('core:whatsapp-webhook')

    @patch('apps.core.tasks.process_message.delay')
    def test_webhook_mensagem_valida(self, mock_task):
        """Testa recebimento de mensagem válida."""
        payload = {
            'from': '+5511999999999',
            'body': 'emitir nota de 150 reais',
            'messageId': 'wamid.123'
        }

        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        # Verificar resposta
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'received'})

        # Verificar que task foi disparada
        mock_task.assert_called_once_with(
            '+5511999999999',
            'emitir nota de 150 reais',
            'wamid.123'
        )

    def test_webhook_payload_invalido(self):
        """Testa payload inválido."""
        payload = {
            'from': '+5511999999999'
            # Faltando campos obrigatórios
        }

        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
```

### Factories

```python
# tests/factories.py
"""
Factories para testes usando factory_boy.
"""
import factory
from factory.django import DjangoModelFactory
from apps.contabilidade.models import Contabilidade, ClienteContabilidade
from apps.core.models import Protocolo
from apps.nfe.models import NotaFiscal

class ContabilidadeFactory(DjangoModelFactory):
    """Factory para Contabilidade."""

    class Meta:
        model = Contabilidade

    cnpj = factory.Sequence(lambda n: f'{n:014d}')
    razao_social = factory.Faker('company', locale='pt_BR')
    nome_fantasia = factory.Faker('company', locale='pt_BR')
    email = factory.Faker('email')
    plano = 'basico'
    status = 'ativo'
    is_active = True

class ClienteContabilidadeFactory(DjangoModelFactory):
    """Factory para ClienteContabilidade."""

    class Meta:
        model = ClienteContabilidade

    contabilidade = factory.SubFactory(ContabilidadeFactory)
    nome = factory.Faker('name', locale='pt_BR')
    telefone = factory.Sequence(lambda n: f'+5511{n:09d}')
    email = factory.Faker('email')

class ProtocoloFactory(DjangoModelFactory):
    """Factory para Protocolo."""

    class Meta:
        model = Protocolo

    contabilidade = factory.SubFactory(ContabilidadeFactory)
    cliente_contabilidade = factory.SubFactory(ClienteContabilidadeFactory)
    telefone_from = factory.SelfAttribute('cliente_contabilidade.telefone')
    mensagem = 'Emitir nota de 150 reais'
    estado_mensagem = 'COLETA'
```

## 📋 Checklist de Testes

Antes de aprovar uma feature:

- [ ] Testes E2E criados e passando (Playwright)
- [ ] Testes unitários para models
- [ ] Testes unitários para services
- [ ] Testes de integração para APIs
- [ ] Multi-tenant isolation testado
- [ ] Edge cases cobertos
- [ ] Error handling testado
- [ ] Responsividade testada (mobile/tablet/desktop)
- [ ] Acessibilidade básica verificada
- [ ] Screenshots capturados para validação visual
- [ ] Coverage > 80% (idealmente 90%)

## 🚀 Comandos Úteis

```bash
# Rodar todos os testes
pytest

# Rodar apenas E2E tests
pytest tests/e2e/

# Rodar apenas unit tests
pytest tests/unit/

# Rodar com coverage
pytest --cov=apps --cov-report=html

# Rodar testes específicos
pytest tests/e2e/test_cliente_crud.py::test_criar_cliente

# Rodar em modo headless (Playwright)
pytest tests/e2e/ --headed

# Rodar com debug
pytest -v -s

# Gerar relatório de coverage
coverage report
coverage html  # Gera HTML em htmlcov/
```

## 📚 Documentação de Referência

- `../03-padroes-codigo.md`: Padrões de teste
- `../05-fluxos-principais.md`: Fluxos para testar
- `../06-desenvolvimento.md`: Configuração de testes
- Playwright docs (via playwright MCP)
- pytest docs (via context7 MCP)
