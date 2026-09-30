"""Built-in guardrail policy presets."""

PRESETS: dict[str, dict] = {
    "minimal": {
        "level": "minimal",
        "filesystem": {
            "deny": ["~/.ssh/**", "~/.aws/**"],
            "confirm_write_outside_scope": False,
        },
        "bash": {
            "block": ["rm -rf /", ":(){ :|:& };:"],
            "confirm": [],
            "allow": ["*"],
        },
        "network": {
            "allow_outbound": True,
        },
        "limits": {
            "max_files_per_turn": 100,
            "max_bash_commands_per_turn": 200,
        },
        "trust": {
            "auto_approve_after": 1,
            "session_scoped": True,
            "persist_patterns": False,
        },
    },
    "standard": {
        "level": "standard",
        "filesystem": {
            "allow": ["~/projects/**", "~/Documents/**", "/tmp/**"],
            "deny": ["~/.ssh/**", "~/.aws/**", "~/.forge/auth/**", "~/.gnupg/**"],
            "confirm_write_outside_scope": True,
        },
        "bash": {
            "block": [
                "rm -rf /",
                ":(){ :|:& };:",
                "curl * | bash",
                "wget * | bash",
                "curl * | sh",
                "wget * | sh",
            ],
            "confirm": [
                "rm",
                "git push",
                "git reset --hard",
                "git force",
                "sudo",
                "docker",
                "pip install",
                "npm install -g",
                "chmod",
                "chown",
                "kill",
                "pkill",
            ],
            "allow": [
                "ls",
                "cat",
                "grep",
                "find",
                "echo",
                "cd",
                "pwd",
                "head",
                "tail",
                "wc",
                "sort",
                "uniq",
                "diff",
                "git status",
                "git log",
                "git diff",
                "git branch",
                "python",
                "node",
                "npm test",
                "pytest",
            ],
        },
        "network": {
            "allow_outbound": False,
            "allowed_hosts": [
                "api.github.com",
                "pypi.org",
                "registry.npmjs.org",
            ],
            "confirm_new_hosts": True,
        },
        "limits": {
            "max_files_per_turn": 20,
            "max_bash_commands_per_turn": 50,
            "cost_limit_session": 5.00,
            "cost_limit_daily": 25.00,
        },
        "trust": {
            "auto_approve_after": 3,
            "session_scoped": True,
            "persist_patterns": False,
        },
    },
    "strict": {
        "level": "strict",
        "filesystem": {
            "allow": [],
            "deny": ["~/.ssh/**", "~/.aws/**", "~/.forge/auth/**", "~/.gnupg/**"],
            "confirm_write_outside_scope": True,
        },
        "bash": {
            "block": [
                "rm -rf /",
                ":(){ :|:& };:",
                "curl * | bash",
                "wget * | bash",
                "curl * | sh",
                "wget * | sh",
                "sudo",
                "docker",
            ],
            "confirm": ["*"],
            "allow": [
                "ls",
                "cat",
                "head",
                "tail",
                "wc",
                "pwd",
                "echo",
            ],
        },
        "network": {
            "allow_outbound": False,
            "allowed_hosts": [],
            "confirm_new_hosts": True,
        },
        "limits": {
            "max_files_per_turn": 10,
            "max_bash_commands_per_turn": 20,
            "cost_limit_session": 2.00,
            "cost_limit_daily": 10.00,
        },
        "trust": {
            "auto_approve_after": 5,
            "session_scoped": True,
            "persist_patterns": False,
        },
    },
}


# SecurityPolicy presets (teotl.core.security) mapped to the closest tool-call
# guardrail preset. A SecurityPolicy object can't be passed to Agent(policy=...):
# the guardrail engine fails to load it and the agent runs with no guardrails.
_GUARDRAIL_FOR_SECURITY_PRESET = {
    "strict": "strict",
    "moderate": "standard",
    "autonomous-dev": "standard",
    "permissive": "minimal",
}


def guardrail_preset_for(preset: object) -> str:
    """Return the guardrail preset to use for a guardrail or SecurityPolicy preset name."""
    if isinstance(preset, str):
        if preset in PRESETS:
            return preset
        return _GUARDRAIL_FOR_SECURITY_PRESET.get(preset, "standard")
    return "standard"
