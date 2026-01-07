# Manual do Usuário - GitHub Downloader

## Visão Geral Técnica

O script utiliza a API pública do GitHub (`api.github.com`) para obter a árvore de arquivos do repositório ("Tree API") e, em seguida, baixa cada arquivo individualmente ("Raw Content") usando a URL `raw.githubusercontent.com`.

### Fluxo de Execução

1. **Validação da URL**: O script analisa a URL fornecida para extrair o proprietário (owner) e o nome do repositório.
2. **Obtenção da Árvore (Tree Fetch)**:
   - Faz uma requisição GET para `https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1`.
   - Se a branch `main` não existir, tenta automaticamente a `master`.
   - Recupera uma lista JSON contendo todos os caminhos de arquivos e diretórios.
3. **Criação de Estrutura**: Itera sobre os diretórios retornados e cria a estrutura localmente.
4. **Download Paralelo**:
   - Utiliza `ThreadPoolExecutor` para iniciar múltiplos downloads simultâneos (padrão: 5 workers).
   - Cada arquivo é baixado via stream para economizar memóriaRAM.
   - Headers `User-Agent` são configurados para evitar bloqueios simples.

## Solução de Problemas

### Erro 403 (Rate Limit)

O GitHub impõe limites para requisições não autenticadas (60 por hora para a API). Se você atingir esse limite, o script avisará.
**Solução**: Aguarde o tempo indicado ou modifique o script para aceitar um Token de Acesso Pessoal (PAT).

### Erro de SSL/TLS

Em redes corporativas com inspeção SSL, você pode receber erros de certificado.
**Solução**:

1. Instale o certificado da raiz da sua empresa no Python `certifi`.
2. OU (não recomendado) desabilite a verificação SSL no script adicionando `verify=False` nas chamadas `requests.get`.

### Arquivos Grandes (LFS)

Este script baixa o conteúdo "raw". Se o arquivo for um ponteiro LFS, você baixará o ponteiro de texto, não o arquivo binário original, pois a API de raw para LFS funciona de forma diferente.

## Opções Avançadas de Linha de Comando

| Argumento | Posição | Descrição                        | Exemplo                        |
| --------- | ------- | -------------------------------- | ------------------------------ |
| URL       | 1       | URL completa do repo             | `https://github.com/vuejs/vue` |
| BRANCH    | 2       | Nome da branch ou tag (opcional) | `v2.6.14`                      |
| OUTPUT    | 3       | Pasta de destino (opcional)      | `src_vue`                      |

Exemplo completo:

```bash
python github_downloader.py https://github.com/vuejs/vue v2.6.14 ./downloads/vue-src
```
