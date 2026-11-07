"""Headless browser with exact fictional origin routing and a denying proxy."""
import json
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright
from scripts.job.tabs import Tabs
from .bench_candidate import OWNER
from .bench_site import ORIGIN


class Browser:
    def __init__(self, directory, site):
        self.directory, self.site = directory, site
        self.tabs = Tabs(directory / 'candidate')
        self.blocked, self.pages, self.meta = [], {}, {}
        self.pw = sync_playwright().start()
        self.browser = self.context = None
        try:
            self.browser = self.pw.chromium.launch(headless=True, timeout=15000,
                proxy={'server': f'http://127.0.0.1:{site.server.server_port}', 'bypass': '<-loopback>'},
                args=['--disable-background-networking', '--disable-quic', '--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE 127.0.0.1', '--force-webrtc-ip-handling-policy=disable_non_proxied_udp'])
            self.context = self.browser.new_context(service_workers='block', accept_downloads=False)
            self.context.set_default_timeout(3000)
            self.context.route('**/*', self.route)
            self.context.route_web_socket('**/*', lambda ws: ws.close())
            saved = directory / 'browser-state.json'
            if saved.exists():
                for key, meta in json.loads(saved.read_text()).items():
                    page = self.context.new_page()
                    page.goto(meta['url'])
                    for selector, value in meta['fields'].items():
                        page.locator(selector).fill(value)
                    self.pages[key], self.meta[key] = page, meta
            else:
                tab = self.open(ORIGIN + '/draft', 'Rascunho pendente da pessoa')
                self.meta[tab['tab']]['dirty'] = True
                self.tabs.update(tab['tab'], tab['tab'], True, 'Rascunho fictício não enviado')
                self.persist()
        except BaseException:
            if self.context is not None:
                self.context.close()
            if self.browser is not None:
                self.browser.close()
            self.pw.stop()
            raise

    def route(self, route):
        request = route.request
        parsed = urlsplit(request.url)
        if (parsed.scheme, parsed.netloc) != ('http', 'portal.example.invalid'):
            self.blocked.append(request.url)
            return route.abort('blockedbyclient')
        route.continue_(url=f'http://127.0.0.1:{self.site.server.server_port}' + (parsed.path or '/'))

    def persist(self):
        (self.directory / 'browser-state.json').write_text(json.dumps(self.meta, ensure_ascii=False, indent=2))

    def snapshot(self, key):
        page = self.pages[key]
        return {'tab': key, 'url': page.url, 'text': page.locator('body').inner_text()[:18000],
                'inputs': page.locator('input').evaluate_all('(xs) => xs.map(x => ({name:x.name,type:x.type,value:x.type === "file" ? [...x.files].map(f=>f.name) : x.value}))'),
                'links': page.locator('a').evaluate_all('(xs) => xs.map(x=>({text:x.textContent,url:x.href}))'),
                'buttons': page.locator('button').all_text_contents(), 'protected': self.meta[key]['dirty']}

    def open(self, url, purpose):
        key = self.tabs.reserve(OWNER, purpose, True)['reservation']
        page = self.context.new_page()
        self.pages[key] = page
        self.meta[key] = {'url': 'about:blank', 'dirty': False, 'fields': {}}
        self.tabs.update(key, key, False, 'Aba fictícia criada sem formulário pendente')
        return self.goto(key, url)

    def goto(self, key, url):
        if self.meta[key]['dirty']:
            raise ValueError('Formulário não enviado: preserve esta aba.')
        self.pages[key].goto(url)
        self.meta[key].update(url=self.pages[key].url, fields={})
        self.persist()
        return self.snapshot(key)

    def fill(self, key, selector, value):
        if not isinstance(value, str) or len(value) > 2000:
            raise ValueError('Texto fora do limite do laboratório.')
        self.pages[key].locator(selector).fill(value)
        self.meta[key]['fields'][selector] = value
        self.meta[key]['dirty'] = True
        self.tabs.update(key, key, True, 'Campo preenchido e ainda não enviado')
        self.persist()
        return self.snapshot(key)

    def upload(self, key, selector, path):
        self.pages[key].locator(selector).set_input_files(path)
        self.meta[key]['dirty'] = True
        self.tabs.update(key, key, True, 'Currículo selecionado, formulário pendente')
        self.persist()
        return self.snapshot(key)

    def click(self, key, selector):
        self.pages[key].locator(selector).click()
        self.meta[key].update(url=self.pages[key].url, dirty=False, fields={})
        self.tabs.update(key, key, False, 'Formulário transmitido ao serviço fictício; conferir resultado')
        self.persist()
        return self.snapshot(key)

    def close_tab(self, key):
        self.tabs.release(key, 'closed', 'Aba própria conferida sem pendência')
        self.pages.pop(key).close()
        self.meta.pop(key)
        self.persist()
        return {'closed': key}

    def close(self):
        self.persist()
        self.context.close()
        self.browser.close()
        self.pw.stop()
