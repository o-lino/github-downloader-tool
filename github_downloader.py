#!/usr/bin/env python3
"""
GitHub Repository Downloader
Baixa todos os arquivos de um repositório GitHub via scraping da interface web.
Útil quando clonagem e downloads 'raw' estão bloqueados.
"""

import os
import sys
import requests
import time
import json
from urllib.parse import urlparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

class GitHubDownloader:
    """Classe para baixar repositórios GitHub via scraping (simula copy-paste)."""
    
    def __init__(self, repo_url: str, output_dir: str = None, branch: str = "main"):
        self.repo_url = repo_url.rstrip('/')
        self.branch = branch
        self.owner, self.repo = self._parse_repo_url()
        self.output_dir = output_dir or self.repo
        self.api_base = "https://api.github.com"
        self.web_base = "https://github.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.stats = {'files': 0, 'dirs': 0, 'errors': 0, 'size': 0, 'skipped': 0}
    
    def _parse_repo_url(self) -> tuple:
        parsed = urlparse(self.repo_url)
        parts = parsed.path.strip('/').split('/')
        if len(parts) < 2:
            raise ValueError(f"URL inválida: {self.repo_url}")
        return parts[0], parts[1].replace('.git', '')
    
    def _get_tree(self, sha: str = None) -> list:
        sha = sha or self.branch
        url = f"{self.api_base}/repos/{self.owner}/{self.repo}/git/trees/{sha}?recursive=1"
        
        response = self.session.get(url)
        if response.status_code == 404:
            if self.branch == "main":
                print(f"⚠️  Branch 'main' não encontrada, tentando 'master'...")
                self.branch = "master"
                return self._get_tree()
            raise Exception(f"Repositório ou branch não encontrado: {self.repo_url}")
        
        if response.status_code == 403:
            raise Exception("Erro de autenticação/limite na API do GitHub. Tente mais tarde.")
            
        return response.json().get('tree', [])
    
    def _scrape_file_content(self, path: str) -> str:
        """
        Acessa a página do arquivo no GitHub e extrai o código do HTML.
        Simula a ação de 'abrir arquivo e copiar texto'.
        """
        # URL da interface web (blob)
        url = f"{self.web_base}/{self.owner}/{self.repo}/blob/{self.branch}/{path}"
        
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Tenta encontrar o textarea (método antigo/simples)
            textarea = soup.find('textarea', {'id': 'read-only-cursor-text-area'})
            if textarea:
                return textarea.get_text()
            
            # Tenta extrair de linhas de tabela (blob-code)
            lines = []
            rows = soup.find_all('td', class_='blob-code-inner')
            if rows:
                for row in rows:
                    lines.append(row.get_text())
                return '\n'.join(lines)
            
            # Tenta extrair do JSON embutido (React view)
            # Procura scripts com data-target="react-app.embeddedData"
            for script in soup.find_all('script', type='application/json'):
                if 'rawLines' in script.text:
                    try:
                        data = json.loads(script.text)
                        # A estrutura do JSON varia, mas geralmente tem payload -> blob -> rawLines
                        if 'payload' in data and 'blob' in data['payload']:
                            if 'rawLines' in data['payload']['blob']:
                                return '\n'.join(data['payload']['blob']['rawLines'])
                    except:
                        pass

            # Se chegou aqui, pode ser um arquivo binário ou vazio
            if "View raw" in response.text or "Download" in response.text:
                return None # Binário
                
            return "" # Vazio
            
        except Exception as e:
            raise Exception(f"Falha no scrape: {e}")

    def _process_item(self, item: dict) -> bool:
        path = item['path']
        file_path = Path(self.output_dir) / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Tenta obter conteúdo via scrape
            content = self._scrape_file_content(path)
            
            if content is None:
                # Arquivo binário ou não textuais
                print(f"   ⚠️  Binário ignorado (scrape mode): {path}")
                self.stats['skipped'] += 1
                return False
                
            # Salva como texto
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            self.stats['files'] += 1
            self.stats['size'] += len(content.encode('utf-8'))
            return True
            
        except Exception as e:
            print(f"   ❌ Erro em {path}: {e}")
            self.stats['errors'] += 1
            return False

    def download(self, max_workers: int = 5):
        print(f"\n� Analisando repositório: {self.owner}/{self.repo}")
        try:
            tree = self._get_tree()
        except Exception as e:
            print(f"❌ Erro: {e}")
            return

        files = [i for i in tree if i['type'] == 'blob']
        print(f"📊 Encontrados: {len(files)} arquivos. Iniciando Scraping Simulado...")
        print("   (Isso é mais lento que download direto pois processa o HTML de cada página)\n")
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._process_item, f): f for f in files}
            
            for i, future in enumerate(as_completed(futures), 1):
                item = futures[future]
                future.result() # O erro é tratado dentro do _process_item
                if i % 5 == 0 or i == len(files):
                     print(f"   Progresso: {i}/{len(files)} ({(i/len(files))*100:.1f}%)")

        elapsed = time.time() - start_time
        print(f"\n✅ Concluído em {elapsed:.2f}s")
        print(f"   Arquivos: {self.stats['files']}")
        print(f"   Skitped (Binários): {self.stats['skipped']}")
        print(f"   Erros: {self.stats['errors']}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python github_downloader.py <URL> [BRANCH] [DESTINO]")
        sys.exit(1)
        
    url = sys.argv[1]
    branch = sys.argv[2] if len(sys.argv) > 2 else "main"
    dest = sys.argv[3] if len(sys.argv) > 3 else None
    
    GitHubDownloader(url, dest, branch).download()
