# 📱 WH INFO — Sistema de Gerenciamento e Vendas

Sistema comercial completo e local (desktop) desenvolvido para lojas de celulares e assistência técnica de informática. O aplicativo roda em um servidor local (Flask) e é acessado pelo navegador, podendo ser empacotado como um executável (`.exe`) para Windows.

## 🚀 Funcionalidades

- **Catálogo Inteligente:** Cadastro de Celulares, Tablets, Acessórios e Serviços, com upload de fotos e importação de imagens da web.
- **Ponto de Venda (PDV):** Carrinho dinâmico que calcula preço de venda, taxas de cartão (débito/crédito), parcelamento e lucro estimado em tempo real.
- **Regras de Negócio:** Margens de lucro personalizáveis (aplicadas a produtos) e margem zero para serviços (apenas taxa da máquina é repassada).
- **Emissão de PDF:** Geração de fichas de venda e comprovantes com identidade visual da loja (ocultando custos e lucros).
- **Controle de Estoque:** Baixa automática de estoque nas vendas e devolução em caso de exclusão de estatísticas de teste.
- **Relatórios:** Faturamento, lucro e produtos mais vendidos por período.
- **Backup e Segurança:** Exportação e restauração do banco de dados e imagens em `.zip`.

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3
- **Backend:** Flask
- **Banco de Dados:** SQLite
- **Interface:** HTML5, CSS3, JavaScript (Vanilla)
- **Geração de PDF:** ReportLab
- **Manipulação de Imagens:** Pillow
- **Empacotamento:** PyInstaller

## 🚀 Como rodar o projeto

- **Passo 1: Clone o repositório**  
  `git clone https://github.com/DeathWing/WH_INFO.git`

- **Passo 2: Crie e ative o ambiente virtual**  
  `python -m venv .venv && .venv\Scripts\activate`

- **Passo 3: Instale as dependências**  
  `pip install -r requirements.txt`

- **Passo 4: Execute o projeto**  
  `python run.py`

## 📂 Estrutura do Projeto

```text
WH_INFO/
├── .vscode/                 # Configurações do VS Code
├── services/                # Regras de negócio e lógicas complexas
│   ├── __init__.py
│   ├── backup.py            # Criação e restauração de backups
│   ├── pdf_generator.py     # Geração das fichas em PDF (ReportLab)
│   ├── pricing.py           # Cálculos matemáticos de margem e taxas
│   └── product_search.py    # Integração com a busca de imagens
├── static/                  # Arquivos visuais e estáticos
│   ├── css/
│   │   └── style.css        # Tema escuro e identidade visual
│   ├── js/
│   │   ├── app.js           # Funções gerais
│   │   ├── calculadora.js   # Lógica da calculadora
│   │   └── sales.js         # Lógica do carrinho e PDV
│   └── images/              # Logo e ícones do sistema
├── templates/               # Telas HTML (Jinja2)
│   ├── base.html            # Layout principal (menu e estrutura)
│   ├── cadastro_produto.html
│   ├── calculadora.html
│   ├── configuracoes.html
│   ├── dashboard.html
│   ├── ficha.html
│   ├── historico.html
│   ├── login.html
│   ├── produtos.html
│   ├── relatorios.html
│   └── vendas.html
├── app.py                   # Rotas do Flask (Controlador principal)
├── build.bat                # Script para gerar o .exe (PyInstaller)
├── config.py                # Configurações de caminhos e variáveis
├── database.py              # Criação e conexão com o SQLite
├── models.py                # Funções de acesso ao banco de dados
├── requirements.txt         # Bibliotecas do Python necessárias
├── run.py                   # Inicializador (abre o navegador e roda o app)
└── .gitignore               # Filtro para não enviar banco/dados ao GitHub
```
---
<div align="center">
  Desenvolvido por <b>Wallysson Costa</b> para a <b>WH INFO</b>.
</div>
