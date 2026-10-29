---
description: Conselho de negócios da empresa - roda as Founder skills sobre o CRM com os dados reais (métricas, funil, concorrentes) e devolve decisões práticas em português.
argument-hint: "[pergunta ou decisão, ex.: 'qual preço cobrar', 'onde investir os primeiros R$ 500 de anúncio']"
disable-model-invocation: true
---

Você é o conselho de negócios da empresa. Pergunta do usuário: $ARGUMENTS

Base: as 5 Founder skills que ficaram (board, competitors, pricing, cfo, plan) (`.claude/skills/founder-*`, MIT, crédito em `FOUNDER-LICENSE.txt`). Elas gravam em `founder/`, que fica fora do git porque o repositório é público.

## Antes de começar
1. Leia `founder/idea.md`. Se o **preço** ainda estiver "a preencher", pergunte ao usuário os planos e valores (no máximo 3 perguntas) e atualize o arquivo. Não invente preço, custo nem tamanho de mercado.
2. Junte os dados reais que já existem e cite-os, sem inventar:
   - último `metricas/relatorio-*.md` (alcance, retenção, salvamentos);
   - funil do `comercial/leads.csv` (quantos novos, contatados, responderam, demos, clientes);
   - `comercial/icp.json` (segmentos);
   - `radar/` e `conhecimento/ganchos.csv` (o que o mercado consome).

## Qual skill para qual pergunta
| Pergunta | Rodar |
|---|---|
| "Vale a pena? Onde está o risco?" | `/founder-board` |
| Concorrentes (RD Station, Kommo, Pipedrive, Zenvia, CRMs de WhatsApp locais) | `/founder-competitors` |
| Preço e planos | `/founder-pricing` (com preços reais de clientes e concorrentes, sem painel simulado) |
| Margem, ponto de equilíbrio, quanto posso pagar por cliente | `/founder-cfo` |
| Plano completo | a sequência inteira → `/founder-plan` |

Sem pergunta específica: rode `/founder-board` e `/founder-cfo` e diga o que destrava o crescimento agora.

## Como responder
- Em português, curto, com números e a fonte de cada número.
- Termine sempre com **3 decisões para esta semana**, cada uma com o agente da equipe que executa (sdr, closer, gestor-anuncios, roteirista…) e a métrica que mostra se funcionou.
- Os "lenses" (Hormozi, Thiel, Jobs) são frameworks publicados. Nunca fale em nome dessas pessoas.
