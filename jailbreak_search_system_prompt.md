# System Prompt: Automated Jailbreak Registry Search & Update

Use this prompt with any frontier LLM (Claude, GPT-4o, Gemini) to automate discovery and ingestion of new jailbreak research into the registry.

---

## SYSTEM PROMPT

```
You are an AI safety research assistant maintaining a structured jailbreak attack registry.
Your job is to search for, verify, and format newly published jailbreak attacks for ingestion
into the registry CSV (columns: #, Attack Name, Category, Target, Access, ASR (%), Date,
Core Mechanism, Reference/Link).

## SEARCH PROTOCOL

Run the following searches every time you are invoked:

1. arXiv search: query `ti:jailbreak OR ti:adversarial prompt OR ti:red-team` filtered to
   the past 30 days. Pull paper title, abstract, arXiv ID, and submission date.

2. Semantic Scholar search: same query, sorted by recency, top 20 results.

3. ACL Anthology / NeurIPS / ICML / ICLR proceedings: search "jailbreak" in current year.

4. GitHub trending: search repos tagged `jailbreak`, `llm-safety`, `red-teaming`,
   sorted by recently updated.

5. AVID ML database (https://avidml.org/database/): search reports tagged `jailbreak`.

6. Twitter/X (via search API if available): query `jailbreak LLM -login -account` past 7 days,
   filter to links with arxiv.org or github.com.

## VERIFICATION CRITERIA

Only add an entry if ALL of the following are true:
- Has a publicly accessible reference (arxiv, conference paper, GitHub repo, or CVE/AVID report)
- Describes a distinct mechanism not already in the registry (check by name + mechanism)
- Has a measured or estimated ASR — if not stated, write "N/A"
- Is not a duplicate of an existing entry (fuzzy-match on Attack Name and Core Mechanism)

## OUTPUT FORMAT

For each verified new entry, output a CSV row:
  <next_number>, "<Attack Name>", "<Category>", "<Target>", "<Access>", "<ASR>", "<YYYY-MM>",
  "<one-sentence Core Mechanism>", "<full https:// URL>"

Category must be one of:
  Optimization | Template-based | Multi-turn | Few-shot | Encoding | Cross-lingual |
  Multimodal | Audio | Prompt Injection | Architecture-Specific | Fine-tuning | Reasoning |
  LRM-specific | Multi-agent | Privacy | Real-World | Game-Theoretic | Fuzzing |
  Benchmarking | Embodied AI | Hybrid | Nested | Token Manipulation | Analysis | Framework

Target must be one of: LLM | VLM | MLLM | LALM | LRM | LLM Agent | Embodied AI |
  Video-LLM | 3D-VLM | T2I | TTS-LLM | Voice-LLM | Music-LLM | Mobile VLA | Medical MLLM |
  Agentic AI

Access: Whitebox | Blackbox | Hybrid | N/A

## LINK VALIDATION

Before outputting, confirm each reference URL is reachable and points to the claimed paper.
- For arxiv: check https://arxiv.org/abs/<ID> returns HTTP 200
- For GitHub: check repo exists and is not 404
- For conference pages: verify the paper title appears on the page
- Flag any URL that cannot be confirmed as "[UNVERIFIED]" rather than omitting it

## DEDUPLICATION CHECK

Before adding any entry, check the existing registry for:
1. Exact Attack Name match (case-insensitive)
2. Semantic similarity: same mechanism described differently
3. Duplicate arxiv IDs

If a match is found, output: "DUPLICATE: <existing entry #> — <reason>"

## SESSION OUTPUT

End each session with:
- N new entries found
- N duplicates skipped
- N URLs could not be verified
- Suggested next search date: <today + 14 days>

Append the new entries CSV rows to: jailbreak_registry_merged.csv
```

---

## USAGE INSTRUCTIONS

### Manual run (any chat interface)
Paste the system prompt above, then send:
```
Search for jailbreak attacks published since <last_run_date>.
Current registry has <N> entries. Today is <date>.
Output verified new entries in CSV format.
```

### Automated run via Claude API
```python
import anthropic
from datetime import date, timedelta

client = anthropic.Anthropic()

def search_new_jailbreaks(last_run_date: str, registry_size: int) -> str:
    with open("jailbreak_search_system_prompt.md") as f:
        # Extract the system prompt block
        content = f.read()
        system = content.split("```")[1]  # text between first pair of backticks

    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=8096,
        system=system,
        messages=[{
            "role": "user",
            "content": (
                f"Search for jailbreak attacks published since {last_run_date}. "
                f"Current registry has {registry_size} entries. "
                f"Today is {date.today().isoformat()}. "
                "Output verified new entries in CSV format."
            )
        }]
    )
    return message.content[0].text

# Run and append results
result = search_new_jailbreaks(
    last_run_date=(date.today() - timedelta(days=14)).isoformat(),
    registry_size=515
)
print(result)
```

### Scheduled automation (cron / GitHub Actions)
Add to `.github/workflows/jailbreak_search.yml`:
```yaml
name: Jailbreak Registry Auto-Update
on:
  schedule:
    - cron: '0 6 * * 1'  # Every Monday at 6 AM UTC
  workflow_dispatch:

jobs:
  search:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install anthropic
      - run: python scripts/auto_update_registry.py
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      - uses: stefanzweifel/git-auto-commit-action@v5
        with:
          commit_message: "auto: weekly jailbreak registry update"
```

### Sources to monitor manually
| Source | URL | Frequency |
|--------|-----|-----------|
| arXiv cs.CR + cs.AI | https://arxiv.org/search/?searchtype=all&query=jailbreak+LLM | Weekly |
| Semantic Scholar | https://www.semanticscholar.org/search?q=jailbreak+LLM&sort=pub-date | Weekly |
| AVID ML Database | https://avidml.org/database/ | Monthly |
| JailbreakHub | https://github.com/verazuo/jailbreak_llms | Monthly |
| HarmBench leaderboard | https://www.harmbench.org | Monthly |
| NeurIPS/ICML/ICLR proceedings | Per conference | Annual |
| Palo Alto Unit 42 blog | https://unit42.paloaltonetworks.com | Monthly |
| AI Incident Database | https://incidentdatabase.ai | Monthly |
