# RLInfraWiki 独立仓库实施总结（Code Review 参考）

Last updated: 2026-06-13

## Review Scope

本次实施将原本内嵌在 `rl-infra-design-agents/.agents/skills/RLInfraWiki/` 的 RLInfraWiki 拆分为顶层独立仓库 `RLInfraWiki/`，并让主仓通过 `.agents/skills/RLInfraWiki` gitlink/submodule-style 依赖固定版本使用它。

执行依据以顶层 `docs/RLInfraWiki独立仓库改进方案_v1_1.md` 为准；`v1.md` 只作为背景和非冲突补充。

## High-Level Changes

- 新建独立 `RLInfraWiki/` skill root，包含 `SKILL.md`、`README.md`、`AGENTS.md`、`CLAUDE.md`、`Makefile`、`pyproject.toml`、`scripts/`、`data/`、`sources/`、`wiki/`、`queries/`、`candidates/`、`artifacts/`、`references/`、`tests/`。
- 主仓 `.agents/skills/RLInfraWiki` 从 tracked embedded files 切换为 gitlink，当前 pinned standalone commit: `7768121`.
- `.gitmodules` 当前使用相对 URL `../RLInfraWiki`，可从主仓 GitHub remote 解析到 sibling 仓库 `https://github.com/byxshr/RLInfraWiki`；该独立远端已发布并包含 pinned commit `7768121`。
- 新增/增强 SourcePack 机制：wiki 正文不再长期引用 `../slime`、`../sglang`、`../verl`、`../ROLL`、`../AReaL` 等本地相对路径；证据改用 source id、repo、commit、repo-relative path、line range、claim id、provenance。
- 将 Wiki 从 framework summary 扩展为 RL infra dictionary，新增首批 concept/capability/interface/algorithm/framework-profile/failure-mode/validation-pattern/adapter-recipe 页面。
- 实现 Context Bundle / Cross-Framework Retrieval 和未知框架适配工具。
- 主仓新增 `make demo`，提升 P0 task workspace 输出质量，并强化 review gate。

## Key Standalone RLInfraWiki Tooling

新增或重构的重点脚本：

- Root resolution: `scripts/_wiki_root.py`，支持脚本位置自动解析和 `RLINFRA_WIKI_ROOT`，配置错误非零退出。
- Context bundle: `compose_context.py`、`validate_context_bundle.py`、`render_context_bundle.py`、`suggest_cross_framework.py`、`trace_related.py`。
- Unknown framework / adapter: `map_framework.py`、`plan_adapter.py`、`diff_capabilities.py`、`compare_frameworks.py`、`search_symbols.py`、`explain.py`、`resolve_alias.py`。
- Source/artifact checks: `verify_source_refs.py`、`verify_artifacts.py`、`extract_source_pack.py`、`migrate_current_rlinfrawiki.py`。
- Existing P0 tools preserved: `query.py`、`get_page.py`、`generate_indices.py`、`validate.py`、`repo_status.py`、task render/review scripts.

## Main Repo Integration

主仓改动重点：

- `Makefile`
  - 新增 `demo` target。
  - `render-example` 使用 `--overwrite-human-docs`，保证 P0 demo 输出展示最新上下文和模板质量。
- `README.md`
  - 新增 submodule init、published sibling remote 说明和可选绝对 URL 配置步骤。
  - 新增 P0 demo quickstart 和 context bundle 手工命令。
- `AGENTS.md` / `CLAUDE.md`
  - 明确 RLInfraWiki 是独立依赖。
  - 强制设计/适配任务先生成并验证 context bundle。
  - 明确 no-target-only 规则。
- `docs/current-project-status.md`
- `docs/project-improvement-status.md`
- `docs/rlinfrawiki-content-status.md`
  - 更新 v1_1 最终方案、canonical 位置、依赖方式、已验证命令和未验证事项。

## Task Bundle / Review Gate Changes

`render_task_bundle.py` 现在为 workspace 写入：

- `context/context_bundle.md`
- `context/context_bundle.json`
- `context/context_sources.yaml`

P0 generated docs now包含：

- primary sync path
- full checkpoint fallback
- `weight_version`
- `flush_cache`
- failure modes
- Wiki page IDs
- source IDs

`validate_review_gate.py` 现在会拒绝：

- 缺 context bundle 三件套。
- context bundle 无法解析或验证失败。
- target-only context。
- 缺 Target / Generic / Cross-Framework / Validation & Risk 四类 pack。
- 缺 page/source ids。
- 缺 validation/risk 覆盖。
- performance/production claim 没有可解析、可验证、包含 validation/risk source coverage 的完整 context bundle。

## Validation Performed

迁移前主仓基线已先跑通：

```bash
conda run -n rl-infra-design-agents make check
conda run -n rl-infra-design-agents make render-example
conda run -n rl-infra-design-agents make review-gate
```

迁移后 standalone `RLInfraWiki/` 验证：

```bash
python scripts/validate.py
python scripts/generate_indices.py --check
python scripts/repo_status.py
python scripts/query.py "GRPO sample fields rollout logprob reward" --limit 8
python scripts/query.py "unknown framework add SGLang rollout backend" --limit 8
python scripts/compose_context.py --target-framework verl --task "add SGLang rollout backend with weight sync" --mode design --output /tmp/context_bundle.md
python scripts/validate_context_bundle.py /tmp/context_bundle.md
python scripts/get_page.py algorithm-grpo --follow-sources
python scripts/get_page.py interface-weight-sync-adapter --follow-sources
python scripts/get_page.py adapter-add-sglang-rollout-backend --follow-sources
python scripts/compare_frameworks.py slime verl roll --capability weight-sync --format markdown
python scripts/map_framework.py --name smoke --repo-root tests/fixtures/minimal_rl_framework --output /tmp/smoke-profile.yaml
python scripts/plan_adapter.py --profile /tmp/smoke-profile.yaml --context /tmp/context_bundle.md --target add-sglang-rollout-backend --output /tmp/smoke-plan.md
python scripts/resolve_alias.py refit
python scripts/suggest_cross_framework.py --capability weight-sync-distributed --target-framework verl --exclude verl
python scripts/trace_related.py framework-verl --depth 2 --relation lessons_from
python scripts/search_symbols.py --repo-root tests/fixtures/minimal_rl_framework --limit 20
python scripts/verify_source_refs.py
python scripts/verify_artifacts.py
conda run -n rl-infra-design-agents pytest -q
```

迁移后主仓验证（最初在 staged working tree 中完成；随后主仓迁移提交为 `38d1602`）：

```bash
git submodule update --init --recursive
conda run -n rl-infra-design-agents make check
conda run -n rl-infra-design-agents make demo
conda run -n rl-infra-design-agents make render-example
conda run -n rl-infra-design-agents make review-gate
```

Observed result:

- 主仓 `make check`: generated indices current, RLInfraWiki validation passed, `45 passed`.
- 主仓 `make demo`: check/render/review/query 全通过，并打印 `/tmp/rl-infra-task-workspace` 和 context bundle 路径。
- Standalone targeted review-gate pytest 在 conda env 中通过：`15 passed`。
- Standalone full pytest 在 conda env 中通过：`45 passed`。

## Known Environment Note

裸 base 环境中的 `pytest` entrypoint 出现过 exit code `139`。使用项目 conda 环境：

```bash
conda run -n rl-infra-design-agents pytest -q
```

可稳定通过。本次验收以该 conda 环境为准。

## Explicit Non-Claims

本次没有验证，也不应在 review 中视为已验证：

- GPU runtime correctness。
- 多机 NCCL。
- 真实分布式 RL training。
- SGLang/Megatron runtime integration。
- 性能、吞吐、延迟、显存或稳定性数据。

所有上游框架行为仍按 `source-reported` 或 `inferred` 处理，除非后续加入本地命令、硬件/上下文、日志/artifact 和结果。

## Reviewer Checklist

重点建议 reviewer 看：

- `.agents/skills/RLInfraWiki` 是否正确作为 gitlink/submodule-style dependency，而不是重新 vendor 旧 tracked tree。
- `.gitmodules` 相对 URL `../RLInfraWiki` 是否符合 README/AGENTS 文档，并可解析到 published sibling remote。
- Standalone `RLInfraWiki/` 是否保持 skill root：根目录直接包含 `SKILL.md`、`scripts/`、`data/`、`sources/`、`wiki/`、`queries/`。
- `scripts/_wiki_root.py` 是否对错误 `RLINFRA_WIKI_ROOT` 非零退出。
- Wiki 正文是否仍残留 `../slime`、`../sglang`、`../verl`、`../ROLL`、`../AReaL` 作为证据路径。
- Context bundle 是否同时包含 Target、Generic、Cross-Framework、Validation & Risk 四类 pack。
- `render_task_bundle.py` 是否保存 context 三件套，且 P0 workspace 是否包含 primary sync path、full fallback、`weight_version`、`flush_cache`、failure modes、page/source IDs。
- `validate_review_gate.py` 是否真正拒绝缺 context、target-only、缺 source/page IDs、缺 validation/risk 的设计。
- P0 `slime + Megatron + SGLang weight sync` query/render/review gate 是否无回退。
- 是否存在任何把 source-reported 写成 verified 的声明。
- 是否存在未验证的 GPU/NCCL/性能/生产可用性 claim。

## Git State Notes

主仓迁移提交 `38d1602` 将旧内嵌 `.agents/skills/RLInfraWiki/**` tracked tree 替换为 `.agents/skills/RLInfraWiki` gitlink 和 `.gitmodules`。这是 expected migration shape：tracked embedded tree 被固定版本依赖取代。

Standalone `RLInfraWiki/` 当前 commit:

```text
7768121 Cover production claim context gate branches
4b81f1b Tighten production claim context gate
c2f7c14 Relax context-backed performance claim gate
38ba820 Initial standalone RLInfraWiki
```

Reviewer follow-up note:

- Round-1 review correctly flagged that `c2f7c14` weakened the performance/production claim gate too far. Follow-up changes restore a parsed/validated context-bundle requirement for risky claims and add a regression test.
- Round-1 review also correctly flagged the absolute `.gitmodules` path. The tracked `.gitmodules` path is now `../RLInfraWiki`, and the sibling remote `https://github.com/byxshr/RLInfraWiki` has been published.
- Round-1 review correctly noted that main-repo validation was collected from staged-but-uncommitted state. The migration has since been committed as `38d1602`.
- Round-2 review found no new blocker. Its P3 coverage question was adopted proactively: standalone commit `7768121` adds direct tests for invalid context bundles, missing validation/risk pack, missing validation/risk source IDs, and missing context_sources validation/risk source map.
- Round-3 review found no new material concern and confirmed the round-2 P3 coverage gap is closed. The follow-up publication step is now complete: standalone remote is published and main migration is committed.
