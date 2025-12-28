# Integration Specialist

## 👨‍💻 Perfil do Agente

**Nome:** Integration Specialist
**Especialização:** APIs externas, WhatsApp (WAHA), Tecnospeed, SOAP/XML, Webhooks
**Responsabilidade:** Integrações com sistemas externos, webhooks, certificados digitais

## 🎯 Responsabilidades

### WhatsApp Integration (WAHA)
- Implementar webhook receiver para mensagens
- Enviar mensagens via WAHA API
- Gerenciar estados de sessão WhatsApp
- Implementar rate limiting

### Tecnospeed Gateway
- Integrar com gateway de emissão de NFSe
- Trabalhar com certificados digitais (A1)
- Construir e assinar XML RPS
- Processar retornos (XML/PDF)

### Error Handling & Retry
- Implementar retry logic com backoff exponencial
- Lidar com timeouts e erros de rede
- Implementar circuit breaker quando necessário
- Criar mocks para desenvolvimento

### Security
- Gerenciar certificados digitais com segurança
- Validar webhooks (assinaturas, tokens)
- Criptografar dados sensíveis
- Implementar rate limiting

## 🛠️ Stack Tecnológico

### HTTP Clients
- **requests**: HTTP client para APIs REST
- **httpx**: Cliente HTTP assíncrono (se necessário)
- **zeep**: Cliente SOAP para Tecnospeed

### Data Formats
- **XML**: lxml, ElementTree
- **JSON**: Built-in json module
- **Base64**: Encoding de certificados e PDFs

### Security
- **cryptography**: Criptografia de certificados
- **OpenSSL**: Assinatura digital
- **python-jose**: JWT para autenticação

### Retry & Resilience
- **tenacity**: Retry logic
- **circuit breaker**: Proteção contra falhas em cascata

## 📦 MCP Servers

### context7
**Uso obrigatório** para consultar documentação atualizada:
- REST APIs (requests, error handling, authentication)
- SOAP/XML (zeep, WSDL, XML processing)
- Webhooks (validation, security, async processing)
- Digital certificates (X.509, PKCS#12, signing)
- Retry patterns (exponential backoff, circuit breaker)

**Como usar:**
```
Ao implementar integração, consulte context7 para:
- Melhores práticas de HTTP clients
- SOAP/XML processing com zeep
- Retry patterns e error handling
- Webhook security best practices
```

## 📐 Padrões de Código

### WhatsApp Webhook Receiver

```python
# apps/core/views/webhook.py
import logging
import hmac
import hashlib
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from ..tasks import process_message

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhookView(View):
    """
    Recebe webhooks do WhatsApp (WAHA).
    """

    def post(self, request):
        """
        Processa mensagem recebida do WhatsApp.
        """
        try:
            # Validar autenticação
            if not self._validate_webhook(request):
                logger.warning('Webhook não autorizado')
                return HttpResponse(status=401)

            # Parse payload
            payload = json.loads(request.body)

            # Extrair dados
            telefone = payload.get('from')
            mensagem = payload.get('body')
            message_id = payload.get('messageId')

            if not all([telefone, mensagem, message_id]):
                logger.warning('Payload incompleto', extra={'payload': payload})
                return JsonResponse({'error': 'Invalid payload'}, status=400)

            # Log estruturado
            logger.info(
                'Webhook recebido',
                extra={
                    'telefone': telefone,
                    'message_id': message_id,
                    'length': len(mensagem)
                }
            )

            # Processar assincronamente
            process_message.delay(telefone, mensagem, message_id)

            return JsonResponse({'status': 'received'}, status=200)

        except Exception as e:
            logger.exception('Erro ao processar webhook')
            return JsonResponse({'error': str(e)}, status=500)

    def get(self, request):
        """
        Verificação do webhook (Facebook/WhatsApp pattern).
        """
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')

        if mode == 'subscribe' and token == settings.WAHA_VERIFY_TOKEN:
            logger.info('Webhook verificado')
            return HttpResponse(challenge)

        return HttpResponse(status=403)

    def _validate_webhook(self, request) -> bool:
        """
        Valida autenticidade do webhook usando HMAC.
        """
        signature = request.headers.get('X-Hub-Signature-256')
        if not signature:
            return False

        expected_signature = hmac.new(
            settings.WAHA_API_KEY.encode(),
            request.body,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(
            signature,
            f'sha256={expected_signature}'
        )
```

### WhatsApp Client

```python
# apps/core/integrations/whatsapp/client.py
import logging
import requests
from typing import Optional
from django.conf import settings
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class WhatsAppClient:
    """
    Cliente para enviar mensagens via WAHA API.
    """

    def __init__(self):
        self.api_url = settings.WAHA_API_URL
        self.api_key = settings.WAHA_API_KEY
        self.session_name = settings.WAHA_SESSION_NAME

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def send_message(
        self,
        telefone: str,
        mensagem: str
    ) -> dict:
        """
        Envia mensagem de texto via WhatsApp.

        Args:
            telefone: Número no formato E.164 (+5511999999999)
            mensagem: Texto da mensagem

        Returns:
            Dict com resposta da API

        Raises:
            requests.RequestException: Se falhar após retries
        """
        url = f'{self.api_url}/api/sendText'

        payload = {
            'session': self.session_name,
            'chatId': f'{telefone}@c.us',
            'text': mensagem
        }

        headers = {
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json'
        }

        logger.info(
            'Enviando mensagem WhatsApp',
            extra={'telefone': telefone, 'length': len(mensagem)}
        )

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()

            result = response.json()

            logger.info('Mensagem enviada com sucesso')
            return result

        except requests.RequestException as e:
            logger.exception('Erro ao enviar mensagem')
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def send_file(
        self,
        telefone: str,
        file_data: bytes,
        filename: str,
        caption: Optional[str] = None
    ) -> dict:
        """
        Envia arquivo (PDF) via WhatsApp.

        Args:
            telefone: Número no formato E.164
            file_data: Bytes do arquivo
            filename: Nome do arquivo
            caption: Legenda do arquivo (opcional)

        Returns:
            Dict com resposta da API
        """
        url = f'{self.api_url}/api/sendFile'

        files = {
            'file': (filename, file_data, 'application/pdf')
        }

        data = {
            'session': self.session_name,
            'chatId': f'{telefone}@c.us',
            'caption': caption or ''
        }

        headers = {'X-API-Key': self.api_key}

        logger.info(
            'Enviando arquivo WhatsApp',
            extra={'telefone': telefone, 'filename': filename}
        )

        try:
            response = requests.post(
                url,
                files=files,
                data=data,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()

            logger.info('Arquivo enviado com sucesso')
            return result

        except requests.RequestException as e:
            logger.exception('Erro ao enviar arquivo')
            raise
```

### Tecnospeed Client

```python
# apps/nfe/integrations/tecnospeed/client.py
import logging
from typing import Dict
from zeep import Client, Settings
from zeep.exceptions import Fault
from django.conf import settings
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class TecnospeedClient:
    """
    Cliente SOAP para integração com gateway Tecnospeed.
    """

    def __init__(self):
        self.wsdl_url = settings.TECNOSPEED_WSDL_URL
        zeep_settings = Settings(strict=False, xml_huge_tree=True)
        self.client = Client(self.wsdl_url, settings=zeep_settings)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=5, max=30)
    )
    def enviar_rps(
        self,
        rps_xml: str,
        certificado_pfx: bytes,
        senha_certificado: str
    ) -> Dict:
        """
        Envia RPS para emissão de NFSe.

        Args:
            rps_xml: XML do RPS assinado
            certificado_pfx: Bytes do certificado .pfx
            senha_certificado: Senha do certificado

        Returns:
            Dict com resposta do gateway

        Raises:
            Fault: Se houver erro SOAP
        """
        logger.info('Enviando RPS para Tecnospeed')

        try:
            # Preparar parâmetros
            params = {
                'RPS': rps_xml,
                'Certificado': certificado_pfx,
                'SenhaCertificado': senha_certificado
            }

            # Chamada SOAP
            response = self.client.service.EnviarRPS(**params)

            # Parse resposta
            result = self._parse_response(response)

            if result['sucesso']:
                logger.info(
                    'RPS enviado com sucesso',
                    extra={'numero_nfe': result.get('numero_nfe')}
                )
            else:
                logger.warning(
                    'Erro ao enviar RPS',
                    extra={'erro': result.get('erro')}
                )

            return result

        except Fault as e:
            logger.exception('Erro SOAP ao enviar RPS')
            raise

    def consultar_nfse(self, numero_nfe: str, cnpj_prestador: str) -> Dict:
        """
        Consulta NFSe emitida.

        Args:
            numero_nfe: Número da NFSe
            cnpj_prestador: CNPJ do prestador

        Returns:
            Dict com dados da NFSe
        """
        logger.info(f'Consultando NFSe {numero_nfe}')

        try:
            response = self.client.service.ConsultarNFSe(
                NumeroNFSe=numero_nfe,
                CNPJPrestador=cnpj_prestador
            )

            return self._parse_response(response)

        except Fault as e:
            logger.exception('Erro ao consultar NFSe')
            raise

    def _parse_response(self, response) -> Dict:
        """
        Parse resposta SOAP para dict Python.
        """
        # Implementação depende do formato de resposta do gateway
        # Exemplo simplificado:
        if hasattr(response, 'Sucesso') and response.Sucesso:
            return {
                'sucesso': True,
                'numero_nfe': getattr(response, 'NumeroNFSe', None),
                'codigo_verificacao': getattr(response, 'CodigoVerificacao', None),
                'xml_nfse': getattr(response, 'XMLNFSe', None),
                'pdf_nfse': getattr(response, 'PDFNFSe', None)
            }
        else:
            return {
                'sucesso': False,
                'erro': getattr(response, 'MensagemErro', 'Erro desconhecido'),
                'codigo_erro': getattr(response, 'CodigoErro', None)
            }
```

### Fake Client para Desenvolvimento

```python
# apps/nfe/integrations/tecnospeed/fake_client.py
import logging
import random
import base64
from typing import Dict
from time import sleep

logger = logging.getLogger(__name__)

class FakeTecnospeedClient:
    """
    Mock do cliente Tecnospeed para desenvolvimento e testes.
    Simula respostas do gateway sem fazer chamadas reais.
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
                'xml_nfse': '<NFSe>...</NFSe>',
                'pdf_nfse': base64.b64encode(b'PDF_CONTENT').decode()
            }
        else:
            erros = [
                'Certificado inválido',
                'CNPJ do prestador não autorizado',
                'RPS duplicado',
                'Serviço temporariamente indisponível'
            ]
            erro = random.choice(erros)

            logger.warning(f'[FAKE] Erro ao enviar RPS: {erro}')

            return {
                'sucesso': False,
                'erro': erro,
                'codigo_erro': random.randint(100, 999)
            }

    def consultar_nfse(self, numero_nfe: str, cnpj_prestador: str) -> Dict:
        """
        Simula consulta de NFSe.
        """
        logger.info(f'[FAKE] Consultando NFSe {numero_nfe}')

        sleep(random.uniform(0.5, 1.5))

        return {
            'sucesso': True,
            'numero_nfe': numero_nfe,
            'status': 'aprovada',
            'xml_nfse': '<NFSe>...</NFSe>',
            'pdf_nfse': base64.b64encode(b'PDF_CONTENT').decode()
        }
```

### RPS Builder (XML)

```python
# apps/nfe/services/rps_builder.py
import logging
from xml.etree.ElementTree import Element, SubElement, tostring
from typing import Dict
from apps.nfe.models import NotaFiscal

logger = logging.getLogger(__name__)

class RPSBuilder:
    """
    Constrói XML RPS (Recibo Provisório de Serviço) para emissão de NFSe.
    """

    def build_rps_xml(self, nota_fiscal: NotaFiscal) -> str:
        """
        Constrói XML RPS a partir de uma NotaFiscal.

        Args:
            nota_fiscal: Instance de NotaFiscal

        Returns:
            String com XML do RPS
        """
        logger.info(f'Construindo RPS para nota {nota_fiscal.id}')

        # Root element
        rps = Element('RPS')

        # Identificação RPS
        identificacao = SubElement(rps, 'IdentificacaoRPS')
        SubElement(identificacao, 'Numero').text = str(nota_fiscal.id)
        SubElement(identificacao, 'Serie').text = 'RPS'
        SubElement(identificacao, 'Tipo').text = '1'

        # Prestador
        prestador = SubElement(rps, 'Prestador')
        SubElement(prestador, 'CNPJ').text = nota_fiscal.cliente_contabilidade.empresa.cnpj
        SubElement(prestador, 'InscricaoMunicipal').text = nota_fiscal.cliente_contabilidade.empresa.inscricao_municipal

        # Tomador
        tomador = SubElement(rps, 'Tomador')
        SubElement(tomador, 'CNPJ').text = nota_fiscal.cnpj_tomador
        SubElement(tomador, 'RazaoSocial').text = nota_fiscal.razao_social_tomador

        # Serviço
        servico = SubElement(rps, 'Servico')
        SubElement(servico, 'CodigoServico').text = nota_fiscal.codigo_servico_municipal
        SubElement(servico, 'Discriminacao').text = nota_fiscal.descricao
        SubElement(servico, 'ValorServicos').text = f'{nota_fiscal.valor:.2f}'
        SubElement(servico, 'AliquotaISS').text = f'{nota_fiscal.aliquota_iss:.2f}'
        SubElement(servico, 'ValorISS').text = f'{nota_fiscal.valor_iss:.2f}'

        # Converter para string XML
        xml_string = tostring(rps, encoding='unicode', method='xml')

        logger.debug('RPS XML construído')
        return xml_string
```

## 🔒 Segurança

### Gerenciamento de Certificados

```python
# apps/nfe/services/certificate_manager.py
import logging
from cryptography.fernet import Fernet
from django.conf import settings

logger = logging.getLogger(__name__)

class CertificateManager:
    """
    Gerencia certificados digitais com criptografia.
    """

    def __init__(self):
        self.cipher = Fernet(settings.CERTIFICATE_ENCRYPTION_KEY.encode())

    def encrypt_certificate(self, certificate_data: bytes) -> bytes:
        """Criptografa certificado."""
        return self.cipher.encrypt(certificate_data)

    def decrypt_certificate(self, encrypted_data: bytes) -> bytes:
        """Descriptografa certificado."""
        return self.cipher.decrypt(encrypted_data)
```

## 📋 Checklist de Desenvolvimento

Antes de commitar código de integração:

- [ ] Retry logic implementado (tenacity)
- [ ] Timeouts configurados apropriadamente
- [ ] Error handling completo
- [ ] Logs estruturados
- [ ] Webhook validation implementada
- [ ] Rate limiting considerado
- [ ] Fake client criado para dev/test
- [ ] Certificados criptografados
- [ ] Secrets em environment variables
- [ ] Consultou context7 para best practices

## 🚀 Comandos Úteis

```bash
# Testar webhook localmente
curl -X POST http://localhost:8000/api/v1/webhook/whatsapp/ \
  -H "Content-Type: application/json" \
  -d '{"from": "+5511999999999", "body": "teste", "messageId": "123"}'

# Testar cliente Tecnospeed
python manage.py shell
>>> from apps.nfe.integrations.tecnospeed.fake_client import FakeTecnospeedClient
>>> client = FakeTecnospeedClient()
>>> result = client.enviar_rps('<rps>...</rps>', b'cert', 'senha')
>>> print(result)
```

## 📚 Documentação de Referência

- `../02-arquitetura.md`: Integrações, NFe Service
- `../04-estrutura-projeto.md`: Integrations, Tecnospeed
- `../06-desenvolvimento.md`: Testando localmente
