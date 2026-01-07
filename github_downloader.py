#!/usr/bin/env python3
"""
GitHub Repository Downloader
Baixa todos os arquivos via Web/HTML Scraping (API-Free).
"""

import os
import sys
import requests
import time
import json
import re
from urllib.parse import urlparse, unquote
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

class GitHubDownloader:
    def __init__(self, repo_url: str, output_dir: str = None, branch: str = "main"):
        self.repo_url = repo_url.rstrip('/')
        self.branch = branch
        self.owner, self.repo = self._parse_repo_url()
        self.output_dir = output_dir or self.repo
        self.web_base = "https://github.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        self.stats = {'files': 0, 'dirs': 0, 'errors': 0, 'size': 0, 'skipped': 0}
        self.visited_dirs = set()

    def _parse_repo_url(self) -> tuple:
        parsed = urlparse(self.repo_url)
        parts = parsed.path.strip('/').split('/')
        if len(parts) < 2:
            raise ValueError(f"URL inválida: {self.repo_url}")
        return parts[0], parts[1].replace('.git', '')

    def _get_page_content(self, url: str) -> BeautifulSoup:
        """Baixa e parseia uma página HTML."""
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            print(f"❌ Erro ao acessar {url}: {e}")
            return None

    def _extract_items_from_payload(self, soup: BeautifulSoup, current_path: str = "") -> list:
        """Tenta extrair itens de diretório do JSON interno (React) ou HTML fallback."""
        items = [] # list of (type, name, path, url)
        
        # 1. Tentar via JSON embutido (mais confiável)
        for script in soup.find_all('script', type='application/json'):
            if 'tree' in script.text and 'items' in script.text:
                try:
                    data = json.loads(script.text)
                    payload = data.get('payload', {})
                    
                    # Navegação na estrutura do payload
                    if 'tree' in payload and 'items' in payload['tree']:
                        for item in payload['tree']['items']:
                            name = item['name']
                            # Path completo
                            full_path = item['path'] 
                            # Determina tipo
                            content_type = item['contentType'] # 'directory' ou 'file'
                            
                            item_type = 'tree' if content_type == 'directory' else 'blob'
                            item_url = f"{self.web_base}/{self.owner}/{self.repo}/{item_type}/{self.branch}/{full_path}"
                            
                            items.append({
                                'type': item_type,
                                'path': full_path,
                                'url': item_url
                            })
                        return items
                except:
                    pass

        # 2. Fallback: Parsear HTML (tabela de arquivos)
        # Seletores comuns do GitHub
        links = soup.select('a.js-navigation-open')
        for link in links:
            href = link.get('href', '')
            if not href: continue
            
            # Filtros básicos para ignorar links de navegação
            if '/commit/' in href or '/commits/' in href or '/blame/' in href:
                continue
            if href.endswith('/..'):
                continue
                
            # Verifica se é parte do repo
            repo_base = f"/{self.owner}/{self.repo}"
            if not href.startswith(repo_base):
                continue
                
            # Identifica blob (arquivo) ou tree (pasta)
            if f"/blob/{self.branch}/" in href:
                item_type = 'blob'
                rel_path = href.split(f"/blob/{self.branch}/", 1)[1]
            elif f"/tree/{self.branch}/" in href:
                item_type = 'tree'
                rel_path = href.split(f"/tree/{self.branch}/", 1)[1]
            else:
                continue
                
            items.append({
                'type': item_type,
                'path': unquote(rel_path),
                'url': self.web_base + href
            })
            
        return items

    def _scrape_file_content(self, url: str) -> str:
        """Extrai conteúdo de arquivo do HTML (blob)."""
        try:
            soup = self._get_page_content(url)
            if not soup: return None
            
            # 1. Tentar via JSON Payload (React)
            for script in soup.find_all('script', type='application/json'):
                if 'rawLines' in script.text:
                    try:
                        data = json.loads(script.text)
                        if 'payload' in data and 'blob' in data['payload']:
                            blob = data['payload']['blob']
                            if 'rawLines' in blob:
                                return '\n'.join(blob['rawLines'])
                            if 'headerInfo' in blob and blob['headerInfo'].get('toc') is None:
                                # Pode ser binário se não tiver rawLines
                                pass
                    except:
                        pass
            
            # 2. Tentar via Tabela HTML (legado/fallback)
            lines = []
            rows = soup.find_all('td', class_='blob-code-inner')
            if rows:
                for row in rows:
                    lines.append(row.get_text())
                return '\n'.join(lines)
            
            # 3. Tentar textarea (muito antigo)
            textarea = soup.find('textarea', {'id': 'read-only-cursor-text-area'})
            if textarea:
                return textarea.get_text()

            return None # Provavelmente binário
            
        except Exception as e:
            print(f"   ⚠️ Falha ao ler {url}: {e}")
            return None

    def crawl_directory(self, dir_url: str):
        """Navega recursivamente nos diretórios."""
        if dir_url in self.visited_dirs:
            return
        self.visited_dirs.add(dir_url)
        
        soup = self._get_page_content(dir_url)
        if not soup: return

        # Extrai items
        items = self._extract_items_from_payload(soup)
        
        files_to_download = []
        dirs_to_visit = []

        for item in items:
            if item['type'] == 'blob':
                files_to_download.append(item)
            elif item['type'] == 'tree':
                dirs_to_visit.append(item)

        # Processa arquivos deste diretório
        if files_to_download:
            print(f"   📂 Processando pasta: {dir_url.split('/')[-1]} ({len(files_to_download)} arquivos)")
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {executor.submit(self._process_file, f): f for f in files_to_download}
                for f in as_completed(futures):
                    pass # Wait completion

        # Recurse (serial para não sobrecarregar)
        for d in dirs_to_visit:
            self.crawl_directory(d['url'])

    def _process_file(self, item: dict):
        path = item['path']
        file_path = Path(self.output_dir) / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        if file_path.exists():
            return # Skip se já existe (opcional)

        content = self._scrape_file_content(item['url'])
        
        if content is not None:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.stats['files'] += 1
                self.stats['size'] += len(content)
                print(f"      ✅ {item['path']}")
            except Exception as e:
                print(f"      ❌ Erro ao salvar {item['path']}: {e}")
        else:
            self.stats['skipped'] += 1
            # print(f"      ⏩ Binário/Ignorado: {item['path']}")

    def start(self):
        print(f"\n🕷️  Iniciando Crawler (API-Free) para: {self.owner}/{self.repo}")
        print(f"Target: {self.web_base}/{self.owner}/{self.repo}/tree/{self.branch}")
        
        start_root = f"{self.web_base}/{self.owner}/{self.repo}/tree/{self.branch}"
        
        # Verifica se o link 'main' funciona, senão tenta master
        if self._get_page_content(start_root) is None:
             if self.branch == 'main':
                 self.branch = 'master'
                 start_root = f"{self.web_base}/{self.owner}/{self.repo}/tree/{self.branch}"
                 print(f"⚠️  Trocando para branch 'master'")
        
        start_time = time.time()
        self.crawl_directory(start_root)
        
        elapsed = time.time() - start_time
        print(f"\n{'='*50}")
        print(f"✅ Concluído em {elapsed:.2f}s")
        print(f"   Arquivos: {self.stats['files']}")
        print(f"   Ignorados (Bin): {self.stats['skipped']}")
        print(f"   Local: {os.path.abspath(self.output_dir)}")
        print(f"{'='*50}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python github_downloader.py <URL> [BRANCH] [DESTINO]")
        sys.exit(1)
        
    url = sys.argv[1]
    branch = sys.argv[2] if len(sys.argv) > 2 else "main"
    dest = sys.argv[3] if len(sys.argv) > 3 else None
    
    GitHubDownloader(url, dest, branch).start()
