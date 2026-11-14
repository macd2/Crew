# Contributing to Crew

Crew is a Hermes Agent plugin with one promise: **you ask once, and a coordinator owns the card until its
proof passes.** The live board (the web dashboard) is a core part of that, not an extra.

Thanks for helping. This file is short on purpose.

## What we want, in order

1. **Bug fixes.** Wrong behavior, crashes, cards that get stuck or are marked done without proof.
2. **Cross-platform.** Windows native, WSL and macOS must work as well as Linux.
3. **Security hardening.** Proof execution, the board server, the installer.
4. **Robustness and the board.** Recovery from failures, clearer board state, fewer ways to lose a card.
5. **New features.**

## Before you start

- Search [existing issues](https://github.com/macd2/Crew/issues) and open pull requests first.
- **Bug fix:** go straight to a PR. Describe how to reproduce it and show the fix works.
- **Small feature:** a PR is welcome. Say how it helps the ask-once flow or the board.
- **Bigger feature** (new command, card contract change, new board view): a short issue first is
  recommended, so we can shape it together before you spend time on code.
- **Security vulnerability:** do not open a public issue or PR. Use private reporting, see
  [SECURITY.md](SECURITY.md).

## Pull requests

- One logical change per PR. No unrelated commits, no drive-by reformatting.
- Use [Conventional Commits](https://www.conventionalcommits.org/): `fix(board): ...`,
  `feat(installer): ...`.
- Add tests where you can. For a bug fix, a test that fails without the fix is ideal.
- A change that reads or writes a new shape of Hermes data (config value, CLI output, board field) adds a row to
  `tests/fixtures/hermes_config_get.json` (or the matching fixture), captured from a real Hermes with
  `python tests/test_hermes_fake_contract.py --refresh`. The test fakes must match real output; a fake written
  from the code under test cannot find the case the code forgot.
- Run the suite and make sure it passes:

  ```
  python -m pytest tests -q
  ```

  Python 3.11+. Some tests build a real kanban board with Hermes's own code, so Hermes must be
  importable (see `.github/workflows/tests.yml` for how CI installs it).
- Fill in the PR template. Say which platform you tested on.

## What happens after you open a PR

- CI on a first-time contributor's PR runs only after a maintainer approves it.
- We respond to every PR and issue within 2 days. A PR that stays quiet for a month may be closed;
  reopen it any time.

## Code style

- Keep the plugin dependency-free beyond Hermes and the standard library unless we've talked it through first.
- Paths, process handling and shell calls must work on Windows, macOS and Linux. No hard-coded
  `/tmp`, no POSIX-only shell in code that runs on user machines.
- Never put machine-specific strings (usernames, hostnames, home paths) in code, tests or docs.

## License

By contributing you agree your work is licensed under the project's Apache-2.0 license.
