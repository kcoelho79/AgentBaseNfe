import httpx
from django.conf import settings


class TecnospeedClient:
    '''Cliente para integração com API Tecnospeed PlugNotas.'''

    BASE_URL = 'https://api.sandbox.plugnotas.com.br'

    def __init__(self):
        self.api_key = getattr(settings, 'TECNOSPEED_API_KEY', '')

    def _headers(self):
        return {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json',
        }

    def cadastrar_certificado(self, arquivo_base64: str, senha: str) -> dict:
        '''
        Cadastra certificado digital na Tecnospeed.

        Args:
            arquivo_base64: Conteúdo do arquivo .pfx em base64
            senha: Senha do certificado

        Returns:
            dict com 'id' do certificado cadastrado
        '''
        url = f'{self.BASE_URL}/certificado'
        payload = {
            'arquivo': arquivo_base64,
            'senha': senha,
        }

        with httpx.Client() as client:
            response = client.post(url, json=payload, headers=self._headers())
            response.raise_for_status()
            return response.json()

    def consultar_certificado(self, certificado_id: str) -> dict:
        '''Consulta informações de um certificado.'''
        url = f'{self.BASE_URL}/certificado/{certificado_id}'

        with httpx.Client() as client:
            response = client.get(url, headers=self._headers())
            response.raise_for_status()
            return response.json()

    def deletar_certificado(self, certificado_id: str) -> bool:
        '''Remove certificado da Tecnospeed.'''
        url = f'{self.BASE_URL}/certificado/{certificado_id}'

        with httpx.Client() as client:
            response = client.delete(url, headers=self._headers())
            return response.status_code == 200

    def cadastrar_empresa(self, dados: dict) -> dict:
        '''
        Cadastra empresa na Tecnospeed.

        Args:
            dados: Dicionário com dados da empresa no formato Tecnospeed

        Returns:
            dict com 'id' da empresa cadastrada
        '''
        url = f'{self.BASE_URL}/empresa'

        with httpx.Client() as client:
            response = client.post(url, json=dados, headers=self._headers())
            response.raise_for_status()
            return response.json()

    def atualizar_empresa(self, empresa_id: str, dados: dict) -> dict:
        '''Atualiza dados de uma empresa.'''
        url = f'{self.BASE_URL}/empresa/{empresa_id}'

        with httpx.Client() as client:
            response = client.patch(url, json=dados, headers=self._headers())
            response.raise_for_status()
            return response.json()
