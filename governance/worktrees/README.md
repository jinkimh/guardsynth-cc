# Git worktree governance

Actual Git worktrees must be outside the main repository:

```text
../guardsynth-cc-worktrees/<work-id>/
```

The main repository's `.worktrees/` directory is reserved for the tracked policy pointer and
registry only. Keeping real worktrees outside prevents repository scans, manifests, search,
Superpowers snapshots, and portal builders from recursively treating worktree files as project
content.

Every worktree gets a unique work ID, project owner, branch, creator, creation date, and status
in `.worktrees/registry.json`. Retire the registry entry after merge and remove the external
worktree with `git worktree remove`.
