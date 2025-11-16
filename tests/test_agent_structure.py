from pathlib import Path

AGENTS_DIR = Path('.github/agents')

REQUIRED_FILES = [
    'echo-bot.agent.md',
    'db-schema.agent.md',
    'finance-rules.agent.md',
    'ui-robustness.agent.md',
    'mcp-tester.agent.md',
    'forensic-searcher.agent.md',
    'code-analyzer.agent.md',
    'generalist.agent.md',
]


def test_agent_files_exist():
    missing = [f for f in REQUIRED_FILES if not (AGENTS_DIR / f).exists()]
    assert not missing, f"Missing agent files: {missing}"


def test_response_contract_presence():
    failures = []
    for fname in REQUIRED_FILES:
        content = (AGENTS_DIR / fname).read_text(encoding='utf-8')
        if 'response_contract>' not in content:
            failures.append(fname)
    # echo-bot and fallback must have response_contract, others too
    assert not failures, f"Files without <response_contract>: {failures}"


def test_manifest_governance_section():
    manifest = Path('AGENTS.MD').read_text(encoding='utf-8')
    assert 'GOVERNANÇA / AUTONOMIA' in manifest, (
        'Governança section absent in AGENTS.MD'
    )
