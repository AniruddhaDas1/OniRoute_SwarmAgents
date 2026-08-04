# OniRoute Examples

These examples are explanatory and are not registered repository artifacts. Install OniRoute first, run them from the repository root, and keep the default Dry Run policy until a local endpoint is intentionally configured.

1. **Hello World:** `oniroute doctor` and `oniroute search architecture`.
2. **Simple Agent:** `oniroute inspect agent backend` and `oniroute context agent backend`.
3. **Workflow execution:** `oniroute plan workflow rest-api-design`, then `oniroute run workflow rest-api-design`.
4. **Context inspection:** `oniroute inspect context rest-api-design`.
5. **Model selection:** `oniroute recommend-model --capability reasoning --local`.
6. **Tool recommendation:** `oniroute recommend-tool --capability database`.
7. **Dry Run:** keep `approval_defaults: Dry Run` in `config/models.yaml`, then run a Workflow and inspect its AI trace.
8. **Governance approval:** compare `oniroute approvals`, `oniroute policy workflow rest-api-design`, and `oniroute explain execution`.
9. **Ollama:** add an Ollama model record/endpoint in local configuration, enable an approved policy, then use `oniroute invoke --model MODEL --prompt "Hello"`.
10. **OpenAI-compatible:** configure a compatible endpoint and model protocol, then invoke through the same command. Do not commit API keys; supply authorization outside repository configuration.
