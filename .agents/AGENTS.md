# Git Push Environment Rule

When executing `git push` or other Git remote operations in this workspace, always clear the `GITHUB_TOKEN` environment variable first (e.g., `$env:GITHUB_TOKEN=$null; git push` in PowerShell). 
The Antigravity execution environment injects a dummy `GITHUB_TOKEN` by default, which overrides the user's valid keychain credentials and causes authentication to fail.
