"""Configuração da camada de testes unitários (tests/unit/).

Registra o marcador "unit" sem alterar o pyproject.toml. Para rodar só esta
camada:  pytest -m unit
"""


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: testes unitários do pacote eren_ml (sem rede, sem banco)")
