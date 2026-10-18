# Guia de Estilo e Identidade Visual: SA-HPL & GSPN Analytics

## 1. Conceito Central

A identidade visual da plataforma prioriza a concentração absoluta do pesquisador nos dados. O design adota um **Dark Theme Moderno e Minimalista**, removendo ruídos visuais e utilizando contraste equilibrado para destacar métricas críticas. A usabilidade é o pilar estrutural, orientada rigorosamente pelas **10 Heurísticas de Nielsen** para garantir que acadêmicos e administradores de infraestrutura operem o sistema com zero curva de aprendizado.

---

## 2. Paleta de Cores (Dark & Menta/Esmeralda)

A composição utiliza o preto fosco como fundação, utilizando tons sobre tons de verde escuro para profundidade e um verde esmeralda suavizado para guiar a atenção (Call-to-Action), evitando fadiga visual.

- **Fundo Principal (Background):** `#0a0a0a` (Preto fosco). Absorve a luz e descansa a visão durante longas análises.
- **Superfícies (Cards, Modais, Dropdowns):** `#111111` (Preto escuro). Cria uma leve elevação em relação ao fundo sem necessidade de sombras pesadas.
- **Cor Primária / Destaque (Confortável):** `#00c868` (Verde Esmeralda Suavizado). Usado para ações primárias (Botão "Executar"), status de Sucesso e linhas principais nos gráficos Plotly. Mantém o destaque sem ser estridente.
- **Tipografia Principal:** `#f5f5f5` (Branco). Para títulos e dados vitais (KPIs).
- **Tipografia Secundária:** `#929292` (Acinzentado claro). Para rótulos de formulários, textos de apoio e eixos de gráficos.
- **Alerta / Erro (Destrutivo):** `#ed646e` (Vermelho Suavizado). Exclusivo para botões de exclusão de histórico e avisos de falha na execução, calibrado para não ser agressivo aos olhos.

---

## 3. Tipografia e Espaçamento

A tipografia deve ser sem serifa (sans-serif), otimizada para legibilidade técnica e números geométricos precisos (essencial para MFLOPs e estatísticas).

- **Família Tipográfica:** `Inter` ou `Roboto Mono` (para tabelas de dados e números).
- **Hierarquia:**
  - **H1 / KPIs (GFLOPs):** 2.5rem, Bold (Branco Puro).
  - **H2 / Títulos de Seção:** 1.5rem, Semi-Bold (Branco Puro).
  - **Body / Texto Padrão:** 1rem, Regular (Secundária - `#929292`).
  - **Microcopy / Rótulos:** 0.85rem, Medium, Uppercase (`#00c868`).
- **Respiro (Whitespace):** O minimalismo exige amplo espaçamento (paddings de `24px` a `32px` dentro dos cards) para evitar a sensação de sobrecarga cognitiva perante gráficos complexos.

---

## 4. Estilização de Componentes

### Botões

- **Ação Principal (Primário):** Fundo verde esmeralda (`#00C868`), texto preto ou verde muito escuro (`#001508`), sem borda, cantos levemente arredondados (`border-radius: 6px`). Efeito _hover_: leve ganho de brilho e redução sutil de opacidade.
- **Ação Secundária:** Fundo transparente, borda de `1px` sólida (`#004D26`), texto branco. Efeito _hover_: fundo muda para `#004D26`.
- **Desabilitado:** Fundo `#0A331C`, texto `#8AB39C` (reduzindo a opacidade em 50%).

### Formulários e Inputs

- **Estado Ocioso:** Fundo `#001508`, borda de `1px` em `#004D26`, texto branco.
- **Estado Ativo (Focus):** Borda iluminada no tom primário (`#00C868`), garantindo clara visualização de onde o cursor está sem ofuscar a visão.
