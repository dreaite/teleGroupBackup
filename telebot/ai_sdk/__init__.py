from .base import AIProvider


def get_ai_provider(config: dict) -> AIProvider | None:
    provider_type = str(config.get('provider', 'openai')).lower()
    
    if provider_type == 'openai':
        from .openai_client import OpenAIClient

        return OpenAIClient(
            api_key=config.get('api_key'),
            base_url=config.get('base_url'),
            model=config.get('model', 'gpt-3.5-turbo')
        )
    if provider_type in {'codex', 'codex_cli', 'codex-cli'}:
        from .codex_cli_client import CodexCLIClient

        return CodexCLIClient(
            command=config.get('codex_command', config.get('command', 'codex')),
            model=config.get('model'),
            profile=config.get('codex_profile'),
            working_dir=config.get('codex_working_dir'),
            timeout_seconds=config.get('codex_timeout_seconds', config.get('timeout_seconds', 900)),
            sandbox=config.get('codex_sandbox', 'read-only'),
            approval_policy=config.get('codex_approval_policy'),
            ephemeral=config.get('codex_ephemeral', True),
            skip_git_repo_check=config.get('codex_skip_git_repo_check', True),
            extra_args=config.get('codex_extra_args', config.get('extra_args')),
        )

    return None
