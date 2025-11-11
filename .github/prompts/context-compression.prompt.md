---
mode: 'agent'
description: 'Analisa a conversa atual e os @todos pendentes, gerando um "meta-prompt" otimizado para continuar a tarefa em um novo chat.'
tools: ['search', 'problems', 'changes', 'todos']
---

# Gerador de Meta-Prompt de Compressão de Contexto

Sua tarefa é analisar **toda esta conversa atual** e **ler os TODOs pendentes (@todos)** para gerar um "Meta-Prompt" em formato Markdown.

O objetivo é permitir que eu (o usuário) inicie um novo chat com todo o contexto essencial (histórico + tarefas pendentes), mas de forma otimizada e enxuta, economizando tokens.

## 🎯 Regras de Análise (O que extrair)

Ao analisar a conversa e os `@todos`, sua saída deve sintetizar exclusivamente os seguintes pontos:

1.  **Objetivo Final:** Qual era o problema principal ou a meta que estávamos tentando alcançar?
2.  **Estado Atual:** Onde a conversa parou? Qual é o último estado funcional do código ou da ideia?
3.  **Testes Falhos (Brevemente):** Resuma brevemente o que já foi tentado e por que não funcionou (ex: "Tentativa de usar a biblioteca X falhou por conflito de dependência").
4.  **Tarefas Pendentes (de @todos):** Extrair todos os itens de `@todos` que ainda estão em aberto E são relevantes para o contexto desta conversa.
5.  **Próximo Passo / Bloqueador:** Qual é a próxima ação lógica (geralmente baseada nos `@todos` ou no último item do chat)?

## 🛑 Restrições (O que NÃO incluir)

Para garantir que o meta-prompt seja "enxuto", você **NÃO DEVE** incluir:

* **NÃO inclua blocos de código-fonte.** (Descreva-os conceitualmente).
* **NÃO inclua o histórico do chat** (ex: "Na mensagem anterior, você me pediu para...").
* **NÃO inclua saudações** ou formalidades.
* **NÃO inclua `@todos` que já foram concluídos** ou que não são relevantes para esta tarefa.

## 📋 Contrato de Saída (Formato Obrigatório do Meta-Prompt)

Gere a saída **exatamente** neste formato Markdown. Este será o prompt que usarei no novo chat.

---
### Meta-Prompt de Continuidade: [Assunto/Projeto]

**Objetivo Principal:**
[Descreva o objetivo final da tarefa aqui]

**Estado Atual:**
[Descreva onde a implementação parou e o que está funcionando]

**O que já falhou (e porquê):**
* **Tentativa:** [Descreva a tentativa que falhou]
* **Motivo:** [Descreva por que falhou]

**Tarefas Pendentes (Importadas de @todos):**
* [ ] [Item 1 pendente extraído dos @todos]
* [ ] [Item 2 pendente extraído dos @todos]
* [ ] [Item 3 pendente extraído dos @todos]

**Próximo Passo / Bloqueador:**
[Descreva a próxima ação clara e imediata ou o problema a ser resolvido, geralmente o primeiro item da lista de TODOs]
---
