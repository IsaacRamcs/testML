# Testes do erenML

- `test_profile.py`: os 13 testes originais do projeto (não alterados).
- `unit/`: camada unitária nova (marcador `unit`). Cobre perfil, pesos, ranking, motor de score e as funções puras do pipeline.

Execução, com cobertura:

```powershell
python -m pytest -q -rxX --cov=eren_ml --cov-report=term --cov-report=html
```

A documentação completa da suíte (as três camadas, como rodar o Robot, a matriz de rastreabilidade, os defeitos e o relatório de execução) está em `../testes_robot/`:

- `../testes_robot/LEIAME_TESTES.md`
- `../testes_robot/MATRIZ_RASTREABILIDADE.md`
- `../testes_robot/DEFEITOS.md`
- `../testes_robot/RELATORIO_EXECUCAO.md`
