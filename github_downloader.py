#!/usr/bin/env python3
"""
GitHub Repository Downloader - Selenium Version
Usa automação de navegador real para baixar repositórios, contornando proxies complexos.
"""

import os
import sys
import time
import json
from pathlib import Path
from urllib.parse import unquote

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

class GitHubDownloader:
    def __init__(self, repo_url: str, output_dir: str = None, branch: str = "main"):
        self.repo_url = repo_url.rstrip('/')
        self.branch = branch
        self.output_dir = output_dir or self.repo_url.split('/')[-1].replace('.git', '')
        self.web_base = "https://github.com"
        
        # stats
        self.stats = {'files': 0, 'dirs': 0, 'errors': 0, 'skipped': 0}
        self.visited_urls = set()

    def _setup_driver(self):
        print("� Iniciando Google Chrome...")
        options = Options()
        # options.add_argument("--headless") # Comentado para permitir interação visual (login proxy)
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--log-level=3")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.set_page_load_timeout(30)
        print("   ✅ Browser iniciado. Se aparecer login de proxy, digite manualmente na janela.")

    def _get_page_type(self, url: str):
        """Determina se é blob (arquivo) ou tree (pasta) pela URL."""
        if f"/blob/{self.branch}/" in url:
            return 'blob'
        if f"/tree/{self.branch}/" in url:
            return 'tree'
        return 'unknown'

    def _wait_for_content(self, timeout=10):
        try:
            # Espera carregar a lista de arquivos ou o blob do arquivo
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.find_elements(By.CSS_SELECTOR, "div.react-directory-filename-column, table.files, div.blob-wrapper, table.highlight") 
                          or d.find_elements(By.CSS_SELECTOR, "script[type='application/json']")
            )
            time.sleep(1) # Extra buffer for heavy JS
        except:
            pass

    def _extract_links_from_dir(self):
        """Extrai links de arquivos e pastas da página atual."""
        links = []
        
        # Tenta pegar via elemento 'a' com classes específicas de navegação
        # GitHub moderno (React) usa classes diferentes, então pegamos genérico e filtramos
        elements = self.driver.find_elements(By.TAG_NAME, "a")
        
        repo_path_part = "/".join(self.repo_url.split('/')[-2:]) # user/repo
        
        for el in elements:
            try:
                href = el.get_attribute("href")
                if not href: continue
                
                # Filtra apenas links relevantes dentro do repo
                if repo_path_part not in href: continue
                if f"/{self.branch}/" not in href: continue
                
                # Ignora links de navegação '..' e commits
                if href.endswith("/.."): continue
                if "/commit/" in href or "/commits/" in href or "/blame/" in href: continue
                
                # Identifica tipo
                if f"/tree/{self.branch}/" in href:
                    links.append({'type': 'tree', 'url': href, 'path': href.split(f"/tree/{self.branch}/")[-1]})
                elif f"/blob/{self.branch}/" in href:
                    links.append({'type': 'blob', 'url': href, 'path': href.split(f"/blob/{self.branch}/")[-1]})
                    
            except:
                continue
                
        # Remove duplicatas preservando ordem
        unique_links = []
        seen = set()
        for l in links:
            if l['url'] not in seen:
                seen.add(l['url'])
                unique_links.append(l)
        
        return unique_links

    def _scrape_file_content(self):
        """Copia conteúdo do arquivo aberto."""
        try:
            # Tenta pegar botão 'Copy raw contents' se existir? Não, melhor ler o DOM.
            
            # 1. Tentar ler linhas da tabela de código
            lines = self.driver.find_elements(By.CSS_SELECTOR, "td.blob-code-inner")
            if lines:
                return "\n".join([line.text for line in lines])
                
            # 2. Tentar ler do textarea (legacy)
            try:
                textarea = self.driver.find_element(By.ID, "read-only-cursor-text-area")
                return textarea.text
            except:
                pass

            # 3. Tentar pegar JSON embedded (React) e parsear (Mais robusto)
            # Como o driver já carregou a página, podemos executar JS para extrair o payload
            try:
                json_content = self.driver.execute_script("""
                    const scripts = document.querySelectorAll('script[type="application/json"]');
                    for (const s of scripts) {
                        if (s.textContent.includes('rawLines')) {
                            return s.textContent;
                        }
                    }
                    return null;
                """)
                if json_content:
                    data = json.loads(json_content)
                    if 'payload' in data and 'blob' in data['payload']:
                         return '\n'.join(data['payload']['blob']['rawLines'])
            except:
                pass
            
            # Se falhar tudo, verifica se é imagem ou binário
            if "View raw" in self.driver.page_source:
                return None # Binário

            return "" # Arquivo vazio
            
        except Exception as e:
            print(f"      ❌ Erro scraping content: {e}")
            return None

    def crawl(self, url):
        """Navegação recursiva (DFS) usando o mesmo browser."""
        if url in self.visited_urls:
            return
        self.visited_urls.add(url)
        
        print(f"👉 Visitando: {url}")
        try:
            self.driver.get(url)
            self._wait_for_content()
            
            page_type = self._get_page_type(url)
            
            if page_type == 'tree': 
                # É diretório
                items = self._extract_links_from_dir()
                
                # Separa arquivos e pastas
                files = [i for i in items if i['type'] == 'blob']
                dirs = [i for i in items if i['type'] == 'tree']
                
                print(f"   📂 Diretório: {len(files)} arquivos, {len(dirs)} subpastas")
                
                # Processa arquivos primeiro (nesta mesma página se possível, mas no selenium temos que navegar)
                # O selenium requer navegação. Então para cada arquivo, vamos e voltamos ou abrimos nova tab?
                # Melhor: Empilha tudo.
                
                # Vamos iterar sobre os links encontrados
                for item in files:
                    self.crawl(item['url'])
                    
                for item in dirs:
                    self.crawl(item['url'])
                    
            elif page_type == 'blob':
                # É arquivo
                rel_path = unquote(url.split(f"/blob/{self.branch}/")[-1])
                file_path = Path(self.output_dir) / rel_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                if file_path.exists():
                     print(f"      ⏩ Já existe: {rel_path}")
                     return

                content = self._scrape_file_content()
                
                if content is not None:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    self.stats['files'] += 1
                    print(f"      ✅ Salvo: {rel_path}")
                else:
                    self.stats['skipped'] += 1
                    print(f"      ⚠️  Binário/Ignorado: {rel_path}")

        except Exception as e:
            print(f"   ❌ Erro em {url}: {e}")
            self.stats['errors'] += 1

    def start(self):
        self._setup_driver()
        
        start_url = f"{self.web_base}/{self.repo_url.split('github.com/')[-1]}/tree/{self.branch}"
        print(f"🎯 Alvo: {start_url}\n")
        
        try:
            self.crawl(start_url)
        except KeyboardInterrupt:
            print("\n🛑 Interrompido pelo usuário.")
        finally:
            print("\n🧹 Fechando navegador...")
            self.driver.quit()
            
            print(f"\n{'='*50}")
            print(f"✅ Concluído")
            print(f"   Arquivos: {self.stats['files']}")
            print(f"   Ignorados: {self.stats['skipped']}")
            print(f"   Local: {os.path.abspath(self.output_dir)}")
            print(f"{'='*50}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python github_downloader.py <URL>")
        sys.exit(1)
        
    url = sys.argv[1]
    branch = "main" # Pode ser melhorado para aceitar args
    
    GitHubDownloader(url, branch=branch).start()
