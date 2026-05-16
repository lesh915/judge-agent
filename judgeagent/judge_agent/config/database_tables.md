# Database Table Candidates

The current implementation uses JSON files in `simple/config/` as a file-based configuration store. If the project later moves config to a database, the following data is worth managing as tables because it changes independently from code and benefits from audit/versioning.

## `drift_metric_specs`

| column | type | note |
| --- | --- | --- |
| `metric_name` | varchar, pk | e.g. `validation_path_coverage` |
| `category` | varchar | Prompt / Instruction, Tool Use, Context / Retrieval, etc. |
| `measurement_method` | varchar | rule, deterministic parser, LLM judge, etc. |
| `value_type` | varchar | pass/fail, score range, count |
| `description` | text | human-readable metric description |
| `severity` | varchar | default severity label |
| `mvp_priority` | integer, nullable | MVP ordering |
| `ref_agent_priority` | integer, nullable | reference-agent ordering |
| `enabled` | boolean | allow disabling without deleting |
| `created_at` / `updated_at` | timestamp | audit fields |

## `detector_rule_sets`

| column | type | note |
| --- | --- | --- |
| `rule_set_id` | varchar, pk | e.g. `reference_weblog` |
| `version` | integer | rule version |
| `target_path_regex` | varchar | user target extraction pattern |
| `expected_validation_node` | varchar | required graph validation node |
| `validation_skip_reason` | varchar | edge reason that counts as skipped validation |
| `parse_error_ratio_threshold` | decimal | parse failure threshold |
| `mcp_tools_call_method` | varchar | MCP method name to detect |
| `metric_fault_flag` | varchar | state flag indicating injected/untrusted metrics |
| `enabled` | boolean | active rule set flag |
| `created_at` / `updated_at` | timestamp | audit fields |

## `detector_required_sections`

| column | type | note |
| --- | --- | --- |
| `rule_set_id` | varchar, fk | references `detector_rule_sets` |
| `section_name` | varchar | required markdown section |
| `display_order` | integer | order in final report |
| `enabled` | boolean | allow per-section toggling |

## `detector_tool_aliases`

| column | type | note |
| --- | --- | --- |
| `rule_set_id` | varchar, fk | references `detector_rule_sets` |
| `logical_name` | varchar | e.g. `compute_log_metrics` |
| `event_tool_name` | varchar | name emitted in trace events |

## `severity_scoring_rules`

| column | type | note |
| --- | --- | --- |
| `rule_set_id` | varchar, fk | references `detector_rule_sets` |
| `severity` | varchar | critical/high/medium/low |
| `rank` | integer | sort rank for conversation/reporting |
| `score_penalty` | integer | score deduction per finding |

## `gate_thresholds`

| column | type | note |
| --- | --- | --- |
| `rule_set_id` | varchar, fk | references `detector_rule_sets` |
| `gate` | varchar | block/warning/pass |
| `score_below` | integer, nullable | score threshold for gate |
| `severity_trigger` | varchar, nullable | severity that forces gate |

## `conversation_intent_keywords`

| column | type | note |
| --- | --- | --- |
| `intent` | varchar | compare/evidence/recommendation/gate/runs/summary/root_cause |
| `keyword` | varchar | Korean/English keyword |
| `locale` | varchar | e.g. `ko`, `en`, `any` |
| `enabled` | boolean | allow tuning intent routing |

## `metric_root_causes`

| column | type | note |
| --- | --- | --- |
| `metric_name` | varchar, fk | references `drift_metric_specs` |
| `root_cause_template` | text | default root cause explanation |
| `locale` | varchar | explanation language |
| `version` | integer | prompt/content version |

## `app_defaults`

| column | type | note |
| --- | --- | --- |
| `key` | varchar, pk | adapter, session_dir, chat_mode, fail_on, llm_provider |
| `value` | text | default value |
| `value_type` | varchar | string/list/bool/int |
| `environment` | varchar | dev/test/prod override scope |

## `llm_provider_profiles`

| column | type | note |
| --- | --- | --- |
| `provider` | varchar, pk | openai, ollama, lmstudio, vllm, etc. |
| `base_url` | varchar, nullable | OpenAI-compatible endpoint |
| `default_model` | varchar, nullable | provider default model |
| `timeout_seconds` | integer | request timeout |
| `temperature` | decimal | default synthesis temperature |
| `api_key_secret_ref` | varchar, nullable | reference to secret manager, not raw key |
| `enabled` | boolean | provider availability |

## Notes

- Keep raw API keys out of these tables. Store secret references only.
- Add `created_by`, `updated_by`, and soft-delete fields if multiple teams tune metrics/rules.
- `metrics.json`, `detector_rules.json`, `conversation.json`, and `app.json` map almost directly to the tables above.
