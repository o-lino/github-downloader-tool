# GitHub Repository Downloader

Uma ferramenta Python simples e eficiente para baixar repositórios públicos do GitHub arquivo por arquivo, mantendo toda a estrutura de diretórios original.

> [!NOTE]
> Esta ferramenta foi criada especificamente para situações onde o `git clone` está bloqueado por políticas de segurança de rede (firewall/proxy), mas o acesso HTTPS ao site do GitHub é permitido.

## 🚀 Funcionalidades

- **Clone sem Git**: Baixa todo o conteúdo sem precisar do protocolo git.
- **Estrutura Preservada**: Mantém a hierarquia exata de pastas e arquivos.
- **Downloads Paralelos**: Usa threads para baixar múltiplos arquivos simultaneamente.
- **Resiliência**: Tenta automaticamente branches alternativas (main/master) e retenta downloads falhos.
- **Sem Dependências Pesadas**: Requer apenas Python e a biblioteca `requests`.

## 📦 Instalação

1. Clone ou baixe este repositório (ou copie o script `github_downloader.py`).
2. Instale as dependências:

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
