
Geral

versão 0.2 = melhorias interface / log / 


CORRECOES/EXMEPLOS unhappy PATH
TENANT
[X] ao criar noma empresa, vai para o menu list empresa e motra todas as empresas
o correto deveria mostrar somente as empresas da contabilidade atual

[ ] se a sessão nao pertecer a nenhum cliente aonde ficara registrado.
[ ] UsuarioEmpresa seu celular cadastrado em duas empresas, nao permitir 

ADMIN
Contabilide
  [x] empresas - deve listar inline os UsuariosEmpresas na tabela ter ter nome/telefone/email



CORE/SESSAO
[ ] Modulo verificar telefone
[x] lista sessao corrigir o filed filtro telefone formato internacional
[x] não esta funcionado expiração validar ver sessao 250126-4cf5


[x] mover templates account/admin/contabilidade para a pasta do app

APP Empresa

[x] /app/empresas trocar cor fonte, coluna razao social do thema claro
[x]  campo CNPJ - link para detail da empresa
[x]  campo CNPJ normalizar deixar salvo 06305747000134 ou 06.305.747/0001-34
[x] menu empresa details menu navtabs incluis os seguintes menus
  [x] Notas fiscal - lista todas as notas da empresa
  [x] Clientes Tomadores - lista ClientesTomadores dessa empresa
[] cadastro de empresa - botao para preencher os dados busca da receita, 
mas não grava no banco (ClienteTomador) 
[] endereço tmb buscar cep - preencher os dados
[x] campo whatsapp cadastro ususario,telefone salva sem o cod paig 
[] cadastro não ativa usuario empresa


NFSE
  [x] criar lista notas emitidas
  [x] criar lista notas processadas
  [x] atualizar menu home notafiscal/emitidas/processadas
  [x] visualizar no menu empresas - notas ficais (notas emitidas)
  [x] criar consulta cnpj
  [x]  Mantive alterar o model clienteTomador => CadastroReceitaCNPJ sugerir
  [x] criar model ClienteTomador CNPJ Fk/ EmpresaID/ Created, Updated, NotaFiscalEfetiva 1:n
  [] criar list ClienteTomador na aba Empresas 
  [] criar list ClienteTomado Menu ClientesTomador tabela numero de notas emitidas
  [] ??? Pensar em lista ClienteTomador para mais de uma empresa, relacionadmento de tabela
  tabela transição clienteId, emprsas n:n notas fiscal
  [ ] menu cliente tomador, esta mostrando de todos os clientes, deveria filtrar
  por contabilidade

Sessoes 
    [x] criar details da sessão  
    [x] desenho do mapeamento dos registrso das sesseos por estado
    [x] infomrações nome e empresa list/details
    [x] filtro buscar por empresa
    [x] filtro por sessoes ativas
     [] salvar os estados nos registors
    [x] refatora os estaos (enum) active-state e termiante-state

Refatorar
    [] ??? reduzris os campos do banco de dados da notas fiscais 
        [] refatorar - prompt (prompt para extração => vallidação manual => prompt para enivar mensagem)

processe

    [x] mensagem sistema => campos preenchdi/campos faltantes 
    [x] mensalge sistema => mudança estados
    

LOG
    [] Criar Informacoes de DEBUG para ver aqruivo LOG
       - entrar no messageProcess - INICIANDO ATENDIMENTO 
       - Sesão Criadada numero ou Sessão Recuperada
       - Estado
          coleta
            - Prompt UserIA 
            - Prompt System
            - Extracao Dados 
                - Dados Extraidos CNPJ Extracted / Valur Formated / Descrição Extracted
                - Dados validados 
                - Dados Mesclados
                  - JSON Final
            - info sempre que for atualizado
            - info salvo no banco 
          Aguardando
              Confirmou
                - SIM
                    Numero Extraction
                    Numero Retorno da nota 
                - NAO
                  - Nota Cancelada
              
Infraestrutura

[ ] Plano 
Atualizar no Git - e salvar no servidor via SSH ou Pensar Docker

versao 0.3
[ ] verificar opção de append erros origem Try, para consulta posterior - pegar erro + linha + modulo ou criar error-level tabela de código de erro
[ ] Criar tabela de erro para debug

Cront tab
# Editar crontab
crontab -e

# Adicionar linha (executar a cada hora):
0 * * * * cd /home/kleber/projetos/AgentBase/mensageria/agentNfe && /caminho/do/python manage.py expire_sessions