# 📦 Sistema de Gestão de Inventário - High Performance Desktop App

Aplicação Desktop para gestão de inventário imobiliário desenvolvida com **Python (Flet)** e **PostgreSQL**. O projeto foca em alta performance de dados, integridade referencial e geração de relatórios gerenciais complexos.

Diferente de sistemas comuns que sofrem com lentidão ao carregar listas, este projeto implementa **cálculos de saldo em tempo real via SQL**, boa normalização de dados e uma interface reativa moderna.

---

## 🧠 Decisões de Arquitetura

### **1. SQL Puro (Raw SQL) vs ORM**
Optei por utilizar **`psycopg2`** com SQL nativo em vez de um ORM completo (como SQLAlchemy). 
*   **O Motivo:** Performance crítica. Para calcular o saldo de 300 itens em tempo real através de milhares de movimentações, queries manuais com agregações (`SUM`, `CASE WHEN`) provaram ser até **100x mais rápidas** do que o processamento via objetos Python, eliminando o problema de "N+1 Queries".

### **2. Lógica de "Ledger" (Razão)**
O sistema **não armazena o saldo atual** dos itens nos apartamentos. 
*   O saldo é **calculado dinamicamente** (Entradas - Saídas). Isso garante integridade absoluta: é impossível o saldo estar dessincronizado com o histórico de movimentações. Se uma movimentação é registrada, o saldo atualiza instantaneamente em todo o sistema.

### **3. Interface com Flet (Flutter)**
Utilizei o Flet para entregar uma experiência de **Single Page Application (SPA)** no Desktop. A interface é construída em Python, mas renderizada com a engine do Flutter, garantindo fluidez, responsividade e uma estética moderna sem a complexidade de frameworks web tradicionais (HTML/CSS/JS).

### **4. Normalização de Dados**
O banco de dados passou por um rigoroso processo de normalização (Fuzzy Matching e Scripts de Migração) para reduzir mais de 700 variações de nomes de itens para uma base consolidada e categorizada, facilitando a gestão e a busca.

---

## 🔒 Pontos Técnicos e Segurança

- **Configuração Externa:** As credenciais do banco de dados são isoladas em um arquivo `config.ini` local, não sendo "chumbadas" no código fonte ou no executável, permitindo fácil troca de ambientes (Dev/Prod).
- **Escrita Atômica de Arquivos:** A geração de relatórios utiliza arquivos temporários e movimentação segura (`shutil.move`) para garantir que PDFs e Excels nunca sejam entregues corrompidos ou com 0 bytes ao usuário.
- **Triggers de Banco:** Automação via PostgreSQL para atualização de timestamps (`updated_at`) e sincronização de nomes de categorias, garantindo consistência mesmo se os dados forem manipulados externamente.

---

## 🛠️ Tecnologias Utilizadas

### **Core**
- **Python 3.12+**: Linguagem base.
- **Flet**: Framework de UI (Baseado em Flutter).
- **PostgreSQL**: Banco de dados relacional robusto.
- **Psycopg2**: Driver de conexão de alta performance.

### **Data & Reporting**
- **Pandas & OpenPyXL**: Manipulação de dados e geração de planilhas Excel complexas.
- **ReportLab**: Geração programática de PDFs com layouts customizados.
- **Matplotlib**: Renderização de gráficos estatísticos (Pizza/Barras) embutidos nos relatórios.

### **Deploy**
- **PyInstaller**: Compilação do código Python para executável (`.exe`) nativo de Windows.

---

## 📊 Destaques de Engenharia

### **1. Otimização de Dashboard**
O carregamento do Dashboard utiliza uma **Single Aggregated Query**. Em vez de iterar sobre cada item para checar o estoque crítico (o que geraria centenas de requisições), o sistema delega a matemática para o motor do PostgreSQL, retornando o status de todo o inventário em milissegundos.

### **2. Exportação Assíncrona com Feedback**
A geração de relatórios inclui uma **UI de Loading** dedicada. Como a criação de gráficos com Matplotlib e a escrita de PDFs pode ser intensiva, o sistema bloqueia a interface e exibe progresso para evitar condições de corrida (cliques duplos) e travamentos aparentes.

### **3. Gerenciamento de Estado**
O aplicativo mantém o estado de navegação e filtros (Paginação, Filtros por Categoria/Status) utilizando referências mutáveis e recarregamento parcial de componentes (`controls.clear()`), garantindo que a memória seja limpa ao transitar entre telas pesadas.

---

## 📂 Estrutura do Projeto

```text
├── app.py                # Ponto de entrada (Main)
├── config.py             # Gerenciador de Configurações (Leitura do .ini)
├── database.py           # Inicialização e Schema do Banco
├── data_service.py       # Camada de Dados (Queries SQL Otimizadas)
├── utils.py              # Utilitários de Sistema (Caminhos, OS)
│
├── apartments_view.py    # Tela de Gestão de Apartamentos e Transferências
├── movements_view.py     # Tela de Histórico de Movimentações (Paginação)
├── items_view.py         # Tela de Catálogo de Itens
├── dashboard_view.py     # Tela de Métricas e KPIs
├── reports_view.py       # Tela de Geração de PDF/Excel
│
└── assets/               # Recursos estáticos (Ícones, Imagens)
    └── exports/          # Pasta de saída dos relatórios
```
---

## 🚀 Como Rodar o Projeto

### 1. Pré-requisitos
- PostgreSQL instalado e rodando.
- Python 3.12+ instalado.

### 2. Configuração do Banco
1. Crie um banco de dados vazio chamado `inventario`.
2. Restaure o arquivo de estrutura/backup fornecido (`database_schema.sql`).

### 3. Instalação e Execução (Dev)
1. Clone o repositório.
2. Instale as dependências: `pip install -r requirements.txt`
3. Crie um arquivo config.ini na raiz:
```text
[DATABASE]
dbname = inventario
user = postgres
password = SUA_SENHA
host = localhost
```

4. Execute: `python app.py`

### 4. Gerar Executável (Deploy)

Para criar a versão de distribuição para o cliente:
`pyinstaller --noconsole --name "GestorInventario" --add-data "assets;assets" --icon="assets/icon.ico" app.py`

A pasta final estará em `dist/GestorInventario`. Lembre-se de incluir o config.ini dentro dela antes de entregar.

---

## ✍️ Autor

Desenvolvido como uma solução robusta para substituir planilhas complexas por um sistema centralizado, seguro e auditável. Foco total em integridade de dados e experiência do usuário desktop