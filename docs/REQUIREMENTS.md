# Especificação de Requisitos: Plataforma Web SA-HPL e GSPN

**Tecnologias Base:** Python (Django), SQLite, Docker, Bootstrap 5.3, Plotly.
**Objetivo:** Plataforma web baseada em contêineres para abstração, parametrização, execução e análise gráfica do benchmark SA-HPL e da modelagem preditiva GSPN.

---

## 1. Requisitos Funcionais (RF)

Estes requisitos descrevem os comportamentos, fluxos e funcionalidades que a aplicação Django deve prover ao usuário final.

| ID       | Nome                                     | Descrição Técnica (Django/Lógica)                                                                                                                                                                                                                                                                                |
| :------- | :--------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **RF01** | **Parametrizar Execução SA-HPL**         | O sistema deve prover um formulário para o usuário definir as variáveis de teste físico: tipo de escalonamento (`scaling_strategy`), nível de concorrência (`num_threads` de 1 a 32) e tamanho da matriz (`array_size`). O Django deve validar estas entradas antes do envio.                                    |
| **RF02** | **Parametrizar Simulação GSPN**          | O sistema deve permitir a configuração de entrada para rodar a predição estocástica (GSPN), validando os mesmos padrões de infraestrutura (threads e estratégia) para simulação teórica.                                                                                                                         |
| **RF03** | **Armazenar Dados da Execução**          | O _Back-End_ (Django ORM) deve criar uma instância do modelo `Execution` e persistir de forma automática no banco SQLite os parâmetros de entrada, _timestamps_ (`started_at`, `finished_at`), status final (`SUCCESS`/`FAILED`), logs de erro e as métricas de saída (ex: `flow_flops`, `estimated_gspn_flow`). |
| **RF04** | **Listar Histórico de Execuções**        | O sistema deve renderizar uma tabela paginada listando todos os registros históricos de execuções armazenados no banco de dados, permitindo a fácil identificação visual do status de cada teste.                                                                                                                |
| **RF05** | **Excluir Execução do Histórico**        | O sistema deve disponibilizar uma ação de deleção (via instrução `DELETE` do ORM). Deve exibir um _modal_ de confirmação no _Front-End_ antes de excluir permanentemente o registro do banco de dados.                                                                                                           |
| **RF06** | **Detalhar Execução Específica**         | O sistema deve possuir uma tela de detalhes (_DetailView_) para exibir a relação completa de parâmetros vs. resultados obtidos de uma única execução, incluindo o rastreamento de erros (`error_detail`), caso a tarefa tenha falhado.                                                                           |
| **RF07** | **Gerar Comparativo Gráfico**            | A aplicação deve permitir a seleção de múltiplas execuções com sucesso e, utilizando a biblioteca **Plotly**, renderizar gráficos interativos na interface comparando a vazão física vs. estimativa teórica.                                                                                                     |
| **RF08** | **Exportar Relatório Consolidado (PDF)** | A partir do histórico selecionado, o _Back-End_ deve formatar um documento PDF estruturado contendo a tabela de consolidação de dados e os gráficos renderizados, forçando o download no navegador.                                                                                                              |

---

## 2. Requisitos Não Funcionais (RNF)

Estes requisitos impõem restrições de qualidade, arquitetura e desempenho na construção do sistema.

| ID        | Categoria                           | Descrição                                                                                                                                                                                                                                                            |
| :-------- | :---------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **RNF01** | **Eficiência (Overhead)**           | A orquestração da plataforma web (Django + SQLite) em execução em _background_ **não deve consumir mais de 5% de CPU e 10% de RAM** do nó hospedeiro, garantindo que as métricas do benchmark não sejam mascaradas.                                                  |
| **RNF02** | **Compatibilidade**                 | O sistema será estritamente conteinerizado. O _host_ deve exigir apenas suporte nativo a **Docker** (Engine >= 20.10.x), sendo agnóstico ao Sistema Operacional.                                                                                                     |
| **RNF03** | **Usabilidade**                     | A interface (_Front-End_ em Bootstrap) deve ser limpa e objetiva. O fluxo de configuração e disparo de testes não deve ultrapassar **3 etapas (telas)** lógicas.                                                                                                     |
| **RNF04** | **Portabilidade**                   | Todo o histórico e as configurações (banco SQLite) devem ser salvos em um **Volume Docker** mapeado. A migração da plataforma para outro cluster/PC deve ocorrer apenas copiando este diretório de volumes.                                                          |
| **RNF05** | **Confiabilidade (Bloqueio Ativo)** | **CRÍTICO:** Durante as execuções (físicas ou simuladas), a aplicação web deve impor um **bloqueio ativo e síncrono da interface** (ex: _loading overlay_ interativo). Novas requisições devem ser bloqueadas para dedicar processamento exclusivo ao contêiner HPC. |
| **RNF06** | **Escalabilidade (Renderização)**   | O navegador do cliente (via Plotly) deve suportar a renderização simultânea de até **20 execuções históricas** em um único gráfico interativo sem gerar _timeouts_ ou travamentos no _Front-End_.                                                                    |

---

## 3. Mapeamento de Telas (Views e Templates Django)

Para contemplar o desenvolvimento completo, a aplicação pode ser dividida logicamente nas seguintes telas (_Templates_):

### Tela 1: `base.html` (Template Pai)

- **Descrição:** Define a estrutura global HTML, importa o Bootstrap 5, Plotly.js e define a barra de navegação (Navbar) padrão.
- **Elementos:** Menu com links para "Nova Execução" e "Histórico".

### Tela 2: `execution_form.html` (Atende RF01, RF02, RNF03, RNF05)

- **Descrição:** Tela com o formulário de configuração.
- **Funcionalidades:**
  - _Inputs:_ `task` (SA-HPL ou GSPN), `scaling_strategy`, `num_threads` e `array_size`.
  - _Ação:_ Ao clicar em "Executar", o JavaScript intercepta o evento, exibe uma **tela de carregamento (Bloqueio Ativo - RNF05)** informando que o servidor está processando, e envia os dados via POST para a _View_ do Django.
  - _Lógica Django:_ Valida o form, aciona o contêiner HPC (via _subprocess_ ou integração Docker), aguarda o término síncrono e salva o Model `Execution`.

### Tela 3: `execution_list.html` (Atende RF04, RF05)

- **Descrição:** Painel principal de registros (Dashboard).
- **Funcionalidades:**
  - Renderiza tabela com colunas: ID, Tipo (SA-HPL/GSPN), Threads, Matriz, Data/Hora e Status (Bagde verde `SUCCESS` ou vermelho `FAILED`).
  - _Ações na linha:_ Botão "Detalhar" (Leva para a Tela 4) e Botão "Excluir" (Abre modal de confirmação do Bootstrap, se confirmado, faz a exclusão POST).
  - _Ação em lote:_ Checkboxes nas linhas para selecionar itens e enviá-los para a Tela 5 (Comparativo).

### Tela 4: `execution_detail.html` (Atende RF06)

- **Descrição:** Visão isolada e minuciosa de um teste.
- **Funcionalidades:**
  - Exibe painéis contendo o _Timestamp_ exato, parâmetros de entrada utilizados e os MFLOPS resultantes.
  - Se a tarefa falhou (`status == 1`), exibe um bloco `<pre><code>` com o rastreamento do erro longo (`error_detail`).

### Tela 5: `execution_compare.html` (Atende RF07, RF08, RNF06)

- **Descrição:** Tela de análise gráfica e relatórios.
- **Funcionalidades:**
  - A _View_ do Django recebe os IDs selecionados na Tela 3, consulta o SQLite e injeta os dados num formato JSON (_context_).
  - O código JS no template usa a biblioteca Plotly para plotar `flow_flops` vs `estimated_gspn_flow`.
  - _Ação:_ Botão "Exportar PDF" que aciona uma rota do Django responsável por gerar o relatório (utilizando bibliotecas como WeasyPrint ou ReportLab) e retornar o arquivo para download.
