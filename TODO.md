
Geral

versão 0.2 = melhorias interface / log / 


[x] mover templates account/admin/contabilidade para a pasta do app

APP Empresa

[x] /app/empresas trocar cor fonte, coluna razao social do thema claro
[x]  campo CNPJ - link para detail da empresa
[x]  campo CNPJ normalizar deixar salvo 06305747000134 ou 06.305.747/0001-34
[x] menu empresa details menu navtabs incluis os seguintes menus
  [x] Notas fiscal - lista todas as notas da empresa
  [x] Clientes Tomadores - lista ClientesTomadores dessa empresa


NFSE
  [x] criar lista notas emitidas
  [x] criar lista notas processadas
  [x] atualizar menu home notafiscal/emitidas/processadas
  [x] visualizar no menu empresas - notas ficais (notas emitidas)
  [x] criar consulta cnpj
  [] alterar o model clienteTomador => CadastroReceitaCNPJ sugerir
  [] criar model ClienteTomador CNPJ Fk/ EmpresaID/ Created, Updated, NotaFiscalEfetiva 1:n
  [] criar list ClienteTomador na aba Empresas 
  [] criar list ClienteTomado Menu ClientesTomador tabela numero de notas emitidas
  [] ??? Pensar em lista ClienteTomador para mais de uma empresa, relacionadmento de tabela
  tabela transição clienteId, emprsas n:n notas fiscal

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