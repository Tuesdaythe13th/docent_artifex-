# Docent Ingestion Plan

## Configuration
- Data path: /Users/tuesday/Library/CloudStorage/GoogleDrive-tuesday@artifex.fun/Shared drives/ARTIFEX LABS/ARC DOWNLOADS /REDTEAM_JUNE4_DEEPSEEKHAR_1210 AM
- API key source: user-supplied (DOCENT_API_KEY env var)

## Source Analysis
- File structure: RTFD bundles (.rtfd directories or zipped .rtfd.zip) exported from macOS AI chat apps
- Detected formats: macOS RTFD — "You said:" / "<Model> responded:" turn structure
- Model detected from filename prefix (DEEPSEEK_, CLAUDE_, GEMINI_, GPT_, etc.)
- Expected source record count: TBD (directory not yet accessible from remote env)

## Docent Model Orientation
- Using custom load_rtfd loader (docent/docent/loaders/load_rtfd.py)
- parse_chat_message used indirectly via UserMessage/AssistantMessage construction

## Proposed Docent Structure
- Collection: REDTEAM_JUNE4_DEEPSEEKHAR (one per red-team session, per user preference)
- AgentRun unit: one per RTFD file (one conversation = one AgentRun)
- TranscriptGroup usage: none (single-model conversations)
- Transcript usage: one per AgentRun

## Field Mapping
| Source | Docent target | Notes |
| --- | --- | --- |
| Filename prefix | metadata.model | e.g. DEEPSEEK_ → "deepseek" |
| Full filename | metadata.source_file | For traceability |
| RTFD bundle name | AgentRun.name | Human-readable run label |
| "You said:" turns | UserMessage | Role: user |
| "<Model> responded:" turns | AssistantMessage (model=detected) | Role: assistant |

## Omitted Data
| Field/File | Reason | Impact |
| --- | --- | --- |
| Attachment.png (screenshots) | Not yet parseable as transcript content | Visual context lost; text intact |
| Date/timestamp markers in RTF | Stripped during cleaning | Intra-session ordering preserved by turn order |

## Confirmation
- Collection name: REDTEAM_JUNE4_DEEPSEEKHAR
- Data context: Red-team session June 4, DeepSeek and other models
- Analysis goals: Cross-model behavior comparison
- User confirmed: pending

## Execution Log

## Verification
- Source records:
- Converted:
- Failed conversions:
- Uploaded:
- Sanity warnings:
- Collection URL:
