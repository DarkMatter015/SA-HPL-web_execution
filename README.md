# SA-HPL & GSPN

## Subir a aplicação web

As dependências Python da aplicação, incluindo ReportLab para exportar o
comparativo em PDF, são instaladas na imagem Docker durante o build.

Depois de alterar `web/requirements.txt`, recrie a imagem e o container:

```powershell
docker compose build --no-cache web
docker compose up --force-recreate web
```

O build valida a importação do ReportLab e falha imediatamente se essa
dependência não estiver instalada. O volume `./web:/usr/local/app` disponibiliza
o código local no container; ele não substitui os pacotes instalados em
`site-packages`.

## Análise e relatórios

As telas de detalhe e comparativo usam gráficos Plotly interativos para
comparar vazão SA-HPL/GSPN por threads e escalonador, escalabilidade, erro
relativo e dispersão por dimensão da matriz. Os filtros atualizam os gráficos,
indicadores e dados exportados. Os PDFs do histórico, da comparação e de uma
execução incluem os cinco painéis como gráficos vetoriais estáticos.
