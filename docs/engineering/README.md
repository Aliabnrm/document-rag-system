# Engineering working agreement

Codex project instructions follow the layered `AGENTS.md` structure described by the [official OpenAI documentation](https://developers.openai.com/codex/guides/agents-md):

- `/AGENTS.md` defines repository-wide product, architecture, quality, Git, documentation, and review rules.
- `/backend/AGENTS.md` specializes backend, worker, persistence, and RAG engineering.
- `/frontend/AGENTS.md` preserves the Next.js-generated guidance and adds the bilingual design-system and UX contract.
- `/infra/AGENTS.md` specializes reproducibility, reliability, security, and operations.
- `/docs/AGENTS.md` defines documentation and sprint-learning standards.

Instructions nearer to the file being edited take precedence when they specialize a repository-wide rule. Keep critical rules concise enough to fit Codex's project-instruction budget, and move explanatory material into normal documentation rather than duplicating it inside every instruction file.

At the end of each sprint, the engineering record must let another contributor answer:

1. What user-visible behavior was delivered?
2. How does one request move through the system?
3. Which architectural decisions were made and why?
4. What failed or changed during implementation?
5. How was correctness and RAG quality measured?
6. What limitations and follow-up work remain?
7. Which backend, AI, frontend, and design-system concepts should a learner retain?
