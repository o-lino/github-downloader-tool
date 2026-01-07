# GitHub Repository Downloader

Uma ferramenta Python simples e eficiente para baixar repositórios públicos do GitHub arquivo por arquivo, mantendo toda a estrutura de diretórios original.

> [!NOTE]
> Esta ferramenta foi criada especificamente para situações onde o `git clone` está bloqueado por políticas de segurança de rede (firewall/proxy), mas o acesso HTTPS ao site do GitHub é permitido.

## 🚀 Funcionalidades

- **Clone via Browser (Selenium)**: Usa uma automação real do Google Chrome.
- **Proxy Friendly**: Usa as configurações de proxy do sistema/browser automaticamente. Permite login manual em janelas de autenticação.
- **Scraping Visual**: Abre cada arquivo no navegador e copia o conteúdo.
- **Sem Git**: Não requer git instalado, apenas o Chrome.

## 📦 Instalação

1. Tenha o **Google Chrome** instalado.
2. Clone ou baixe este repositório.
3. Instale as dependências:

```bash
pip install -r requirements.txt
```

## 🛠️ Como Usar

Você pode usar a ferramenta de duas formas:

### 1. Modo Interativo

Basta rodar o script sem argumentos e seguir as instruções na tela:

```bash
python github_downloader.py
```

### 2. Linha de Comando

Passe a URL e (opcionalmente) a branch e diretório de destino:

```bash
# Uso básico
python github_downloader.py https://github.com/facebook/react

# Especificando a branch
python github_downloader.py https://github.com/facebook/react 18.2.0

# Especificando destino personalizado
python github_downloader.py https://github.com/facebook/react main ./meu-projeto
```

## 📋 Requisitos

- Python 3.6+
- Conexão com a internet (HTTPS liberado para `api.github.com` e `raw.githubusercontent.com`)

## 📄 Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.
