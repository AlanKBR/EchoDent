
# EchoDent - Relatório de Não Conformidades (Offline-First)

## Prioridade Alta
1. **Logging estruturado ausente**
   - Risco: Falta de rastreabilidade e auditoria robusta.
   - Ação: Implementar sistema de logs seguro (ex: Python logging, arquivos rotativos).

2. **Validação insuficiente de uploads de mídia**
   - Risco: Possível execução de arquivos maliciosos ou sobrecarga local.
   - Ação: Checar tipo, tamanho e extensão dos arquivos enviados.

3. **Falta de rate limiting na autenticação**
   - Risco: Vulnerabilidade a brute force, mesmo em rede local.
   - Ação: Adicionar limitação de tentativas e bloqueio temporário.

4. **Falta de headers de segurança nas respostas HTTP**
   - Risco: Exposição a ataques via navegador (CSP, HSTS, X-Content-Type-Options).
   - Ação: Configurar headers essenciais em todas respostas.

5. **Falta de proteção CSRF em formulários**
   - Risco: Possível envio de requisições maliciosas via navegador.
   - Ação: Garantir uso de CSRF token em todos formulários POST.

6. **Escapes insuficientes em templates Jinja e swaps HTMX**
   - Risco: Vetor potencial para XSS se variáveis não forem sempre escapadas.
   - Ação: Revisar templates e garantir escapes automáticos, evitar uso de `|safe`/`|raw` sem sanitização.

7. **Ausência de política de backup/restauração dos bancos SQLite**
   - Risco: Perda total de dados em caso de falha física ou corrupção.
   - Ação: Implementar rotina automatizada de backup/restauração local.

8. **Falta de logging detalhado de acesso administrativo**
   - Risco: Dificuldade de rastrear ações críticas e possíveis abusos.
   - Ação: Logar todas ações de usuários admin, especialmente alterações financeiras e de dados sensíveis.

9. **Ausência de política de expiração de sessão**
   - Risco: Sessões podem permanecer abertas indefinidamente, aumentando risco de uso indevido.
   - Ação: Definir timeout de sessão e exigir reautenticação após período de inatividade.

10. **Falta de auditoria explícita para alterações críticas**
   - Risco: Mudanças em dados financeiros ou clínicos podem passar despercebidas.
   - Ação: Garantir que toda alteração relevante seja registrada com usuário, timestamp e motivo.

11. **Ausência de validação de timezone em todas datas**
   - Risco: Inconsistências em registros e relatórios, especialmente em ambientes multiusuário.
   - Ação: Validar e normalizar timezone em todos campos de data/hora.

12. **Ausência de validação de conteúdo real em uploads de imagem**
   - Risco: Upload de arquivos disfarçados pode comprometer integridade do sistema.
   - Ação: Verificar magic bytes/conteúdo real dos arquivos além da extensão.

13. **Ausência de documentação dos endpoints sensíveis**
   - Risco: Dificulta revisão de segurança e onboarding de novos desenvolvedores.
   - Ação: Documentar endpoints críticos e fluxos de autenticação/autorização.

14. **Ausência de política de atualização de dependências**
   - Risco: Dependências desatualizadas podem conter vulnerabilidades conhecidas.
   - Ação: Implementar rotina de atualização e auditoria periódica (ex: pip-audit, dependabot).

15. **Falta de verificação de integridade dos arquivos estáticos**
   - Risco: Possível tampering/local defacement sem detecção.
   - Ação: Validar integridade (hash/checksum) dos arquivos estáticos críticos.

16. **Ausência de limitação de tamanho de requisições HTTP**
   - Risco: Possível DoS local por requisições excessivamente grandes.
   - Ação: Definir limites de tamanho para uploads e payloads.

17. **Ausência de sanitização de logs**
   - Risco: Log injection pode comprometer auditoria e análise.
   - Ação: Sanitizar entradas antes de registrar em logs.

18. **Ausência de validação de encoding em uploads/textos**
   - Risco: Dados corrompidos ou ataques via encoding malicioso.
   - Ação: Validar e normalizar encoding de todos textos e arquivos recebidos.

19. **Falta de segregação clara de ambientes DEV/PROD**
   - Risco: Recursos de desenvolvimento podem ser expostos em produção.
   - Ação: Garantir flags, variáveis e rotas DEV bloqueadas em produção.

20. **Ausência de política de retenção de dados**
   - Risco: Dados sensíveis podem ser mantidos indefinidamente sem necessidade.
   - Ação: Definir e implementar política de retenção e descarte seguro.

21. **Ausência de controle de permissões granulares por papel**
   - Risco: Usuários podem executar ações além do necessário para seu papel.
   - Ação: Revisar e restringir permissões por perfil/role.

22. **Ausência de verificação de unicidade em campos críticos**
   - Risco: Duplicidade de emails, usernames ou outros identificadores pode causar inconsistências.
   - Ação: Garantir unicidade via constraints e validação de input.

23. **Falta de testes de stress/concurrency**
   - Risco: Comportamento imprevisível sob carga ou concorrência.
   - Ação: Implementar testes automatizados de stress e concorrência.

## Prioridade Média
1. **Cache apenas in-memory**
   - Risco: Perda de dados em reinicialização ou concorrência.
   - Ação: Avaliar uso de Redis/Memcached se multi-instância.

2. **Falta de cache busting/versionamento para assets estáticos**
   - Risco: Possível carregamento de assets desatualizados.
   - Ação: Implementar versionamento se houver atualizações frequentes.

3. **Scripts de seed/teste com senhas simples e hardcoded**
   - Risco: Uso acidental em produção pode expor credenciais fracas.
   - Ação: Garantir que scripts de DEV nunca sejam usados em ambiente produtivo.

4. **Tokens de serviços externos opcionais podem ser expostos**
   - Risco: Se não configurados corretamente, podem ser acessados por código ou logs.
   - Ação: Validar configuração segura e uso restrito.

## Prioridade Baixa
1. **Monitoramento automatizado de performance ausente**
   - Risco: Dificuldade de diagnóstico em produção/cloud.
   - Ação: Planejar integração futura com Prometheus/Grafana.

2. **Proteção contra SSRF não implementada**
   - Risco: Irrelevante no contexto atual, mas importante para cloud.

3. **Criptografia de dados sensíveis em disco**
   - Risco: Exposição em caso de acesso físico ao disco.
   - Ação: Avaliar criptografia para dados críticos.

4. **Testes automatizados para cenários de segurança ausentes**
   - Risco: Possível regressão de segurança.
   - Ação: Priorizar após correção dos itens acima.

5. **Manipulação de localStorage em JS para temas**
   - Risco: Vetor para manipulação de estado ou dados sensíveis se expandido.
   - Ação: Monitorar e restringir uso apenas para dados não críticos.

## Resumo
Priorize os itens de alta prioridade para garantir robustez e segurança local. Os demais podem ser planejados conforme o app evoluir para ambientes online ou distribuídos.
