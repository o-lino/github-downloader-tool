#!/usr/bin/env python3
"""
GitHub Repository Downloader
Baixa todos os arquivos de um repositório GitHub público mantendo a estrutura de pastas.
Útil quando clonagem via git está bloqueada por políticas de segurança.
"""

import os
import sys
import requests
import time
from urllib.parse import urlparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


class GitHubDownloader:
    """Classe para baixar repositórios GitHub sem usar git clone."""
    
    def __init__(self, repo_url: str, output_dir: str = None, branch: str = "main"):
        """
        Inicializa o downloader.
        
        Args:
            repo_url: URL do repositório GitHub (ex: https://github.com/user/repo)
            output_dir: Diretório de saída (padrão: nome do repositório)
            branch: Branch a ser baixado (padrão: main)
        """
        self.repo_url = repo_url.rstrip('/')
        self.branch = branch
        self.owner, self.repo = self._parse_repo_url()
        self.output_dir = output_dir or self.repo
        self.api_base = "https://api.github.com"
        self.raw_base = "https://raw.githubusercontent.com"
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHub-Repo-Downloader'
        })
        self.stats = {'files': 0, 'dirs': 0, 'errors': 0, 'size': 0}
    
    def _parse_repo_url(self) -> tuple:
        """Extrai owner e repo da URL."""
        parsed = urlparse(self.repo_url)
        parts = parsed.path.strip('/').split('/')
        if len(parts) < 2:
            raise ValueError(f"URL inválida: {self.repo_url}")
        return parts[0], parts[1].replace('.git', '')
    
    def _get_tree(self, sha: str = None) -> list:
        """Obtém a árvore completa do repositório."""
        sha = sha or self.branch
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/git/trees/{sha}?recursive=1"
        
        response = self.session.get(url)
        
        if response.status_code == 404:
            # Tenta com 'master' se 'main' falhar
            if self.branch == "main":
                print(f"⚠️  Branch 'main' não encontrada, tentando 'master'...")
                self.branch = "master"
                return self._get_tree()
            raise Exception(f"Repositório ou branch não encontrado: {self.repo_url}")
        
        if response.status_code == 403:
            reset_time = response.headers.get('X-RateLimit-Reset')
            raise Exception(f"Rate limit excedido. Tente novamente após: {reset_time}")
        
        response.raise_for_status()
        return response.json().get('tree', [])
    
    def _download_file(self, item: dict) -> bool:
        """Baixa um único arquivo."""
        path = item['path']
        file_path = Path(self.output_dir) / path
        
        # Cria diretório pai se necessário
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # URL para download do arquivo raw
        raw_url = f"{self.raw_base}/{self.owner}/{self.repo}/{self.branch}/{path}"
        
        try:
            response = self.session.get(raw_url, stream=True)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            size = item.get('size', 0)
            self.stats['size'] += size
            return True
            
        except Exception as e:
            print(f"   ❌ Erro ao baixar {path}: {e}")
            self.stats['errors'] += 1
            return False
    
    def download(self, max_workers: int = 5) -> dict:
        """
        Baixa o repositório completo.
        
        Args:
            max_workers: Número de downloads paralelos
            
        Returns:
            Estatísticas do download
        """
        print(f"\n🔍 Analisando repositório: {self.owner}/{self.repo}")
        print(f"📁 Branch: {self.branch}")
        print(f"💾 Destino: {self.output_dir}\n")
        
        # Obtém árvore do repositório
        try:
            tree = self._get_tree()
        except Exception as e:
            print(f"❌ Erro: {e}")
            return self.stats
        
        # Separa arquivos e diretórios
        files = [item for item in tree if item['type'] == 'blob']
        dirs = [item for item in tree if item['type'] == 'tree']
        
        print(f"📊 Encontrados: {len(files)} arquivos em {len(dirs)} diretórios\n")
        
        # Cria diretório de saída
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        # Cria estrutura de diretórios
        for dir_item in dirs:
            dir_path = Path(self.output_dir) / dir_item['path']
            dir_path.mkdir(parents=True, exist_ok=True)
            self.stats['dirs'] += 1
        
        # Download paralelo dos arquivos
        print("⬇️  Baixando arquivos...")
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._download_file, f): f for f in files}
            
            for i, future in enumerate(as_completed(futures), 1):
                item = futures[future]
                success = future.result()
                if success:
                    self.stats['files'] += 1
                    # Mostra progresso
                    progress = (i / len(files)) * 100
                    print(f"   [{i}/{len(files)}] ({progress:.1f}%) ✅ {item['path']}")
        
        elapsed = time.time() - start_time
        
        # Resumo final
        print(f"\n{'='*50}")
        print(f"✅ Download concluído em {elapsed:.2f}s")
        print(f"   📁 Diretórios criados: {self.stats['dirs']}")
        print(f"   📄 Arquivos baixados: {self.stats['files']}")
        print(f"   💾 Tamanho total: {self._format_size(self.stats['size'])}")
        if self.stats['errors'] > 0:
            print(f"   ❌ Erros: {self.stats['errors']}")
        print(f"   📂 Local: {os.path.abspath(self.output_dir)}")
        print(f"{'='*50}\n")
        
        return self.stats
    
    def _format_size(self, size: int) -> str:
        """Formata tamanho em bytes para formato legível."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"


def main():
    """Função principal."""
    print("\n" + "="*50)
    print("🐙 GitHub Repository Downloader")
    print("="*50)
    
    # Obtém URL do repositório
    if len(sys.argv) > 1:
        repo_url = sys.argv[1]
    else:
        repo_url = input("\n📎 Cole a URL do repositório GitHub: ").strip()
    
    if not repo_url:
        print("❌ URL não fornecida!")
        sys.exit(1)
    
    # Obtém branch (opcional)
    branch = "main"
    if len(sys.argv) > 2:
        branch = sys.argv[2]
    elif len(sys.argv) == 1:
        branch_input = input("🌿 Branch (pressione Enter para 'main'): ").strip()
        if branch_input:
            branch = branch_input
    
    # Obtém diretório de saída (opcional)
    output_dir = None
    if len(sys.argv) > 3:
        output_dir = sys.argv[3]
    elif len(sys.argv) == 1:
        output_input = input("📁 Diretório de saída (pressione Enter para usar nome do repo): ").strip()
        if output_input:
            output_dir = output_input
    
    try:
        downloader = GitHubDownloader(repo_url, output_dir, branch)
        downloader.download()
    except KeyboardInterrupt:
        print("\n\n⚠️  Download cancelado pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
