import tempfile
import unittest
from pathlib import Path

from scripts.job.tabs import Tabs


class TabTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='job-tabs-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.tabs = Tabs(self.root)

    def test_limit_survives_restart_and_read_does_not_create_data(self):
        self.assertEqual(self.tabs.status()['available'], 2)
        self.assertFalse((self.root / '.job').exists())
        self.tabs.reserve('agent:one', 'Pesquisa fictícia', True)
        self.tabs.reserve('agent:two', 'Retorno fictício', True)
        with self.assertRaisesRegex(ValueError, 'Limite'):
            Tabs(self.root).reserve('agent:three', 'Outra busca', True)
        self.assertEqual(Tabs(self.root).status()['in_use'], 2)

    def test_pending_and_user_tabs_cannot_be_closed(self):
        key = self.tabs.reserve('agent:one', 'Formulário fictício', True)['reservation']
        self.tabs.update(key, 'browser:tab-1', True, 'Há um formulário não salvo.')
        with self.assertRaises(ValueError):
            self.tabs.release(key, 'closed', 'Quero abrir outra vaga.')
        with self.assertRaises(ValueError):
            self.tabs.release(key, 'returned_to_user', 'Aguardando login.')
        self.tabs.update(key, 'browser:tab-1', False, 'Envio confirmado e registrado.')
        self.tabs.release(key, 'closed', 'Ferramenta confirmou o fechamento da aba própria.')
        user = self.tabs.reserve('agent:one', 'Sessão já aberta da pessoa', False)['reservation']
        self.tabs.update(user, 'browser:user-tab', False, 'A consulta terminou.')
        with self.assertRaises(ValueError):
            self.tabs.release(user, 'closed', 'Consulta terminou.')
        self.tabs.release(user, 'returned_to_user', 'Interação encerrada, aba preservada.')
        self.assertEqual(self.tabs.status()['available'], 2)

    def test_unknown_creation_and_duplicate_identity_stay_reserved(self):
        one = self.tabs.reserve('agent:one', 'Busca', True)['reservation']
        two = self.tabs.reserve('agent:two', 'Outra busca', True)['reservation']
        self.tabs.update(one, 'browser:tab-1', True, 'Aba criada.')
        with self.assertRaises(ValueError):
            self.tabs.update(two, 'browser:tab-1', False, 'Identidade duplicada.')
        with self.assertRaises(ValueError):
            self.tabs.release(one, 'not_created', 'Estado desconhecido.')
        self.tabs.release(two, 'not_created', 'Ferramenta confirmou falha antes de criar a aba.')
        self.tabs.release(one, 'already_absent', 'Inventário do navegador confirma que a aba foi fechada pela pessoa.')
        self.assertEqual(self.tabs.status()['available'], 2)
