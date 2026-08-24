# Outreach Assistant

Outreach Assistant is a Python learning and portfolio project for organizing responsible, human-reviewed outreach.

The repository began as an experimental Selenium automation system for Instagram and TikTok. It is now being redesigned into a local outreach assistant that helps a person manage contacts, prepare personalized drafts, record outcomes, and remember follow-ups. It is not intended for bulk messaging, unsolicited spam, private-data scraping, or unattended sending.

## Project status

**Redesign in progress.**

The repository currently contains working component-level code from the original browser-automation prototype, including SQLite storage, rate limiting, retry logic, session checkpoints, platform adapters, selectors, and message templates. The component test suite passes in the expected package layout, but the live browser workflow has not been revalidated as a safe production application.

The next version will prioritize a clear contact-management and draft-review workflow over automatic platform actions. Later milestones may automate approved workflow steps through supported integrations while preserving the human approval boundary.

## Responsible-use principles

- A person must review and approve every message before it is sent.
- The application will not send a message without explicit human approval.
- The application will not scrape private or restricted data.
- Contacts should be added only from legitimate, permission-based sources.
- API keys, passwords, browser sessions, customer data, and proxy credentials must never be committed to Git.
- Local databases, logs, screenshots, checkpoints, and working CSV files are excluded through `.gitignore`.

## Planned workflow

```text
Add or import an appropriate contact
              |
              v
Prepare a personalized draft
              |
              v
Human reviews and edits the message
              |
              v
Human explicitly approves the message
              |
              v
Send manually or through an authorized integration
              |
              v
Record delivery, notes, reply, and follow-up date
```

## Portfolio MVP

The first portfolio-ready version will provide:

- Contact creation and editing
- Statuses such as `Not contacted`, `Drafted`, `Sent`, and `Replied`
- Personalized message drafts
- Mandatory human review and approval before sending
- Notes and activity history
- Follow-up reminders
- CSV import and export
- Local SQLite storage
- Automated tests for core workflows

## Existing technical components

| Area | Location | Purpose |
| --- | --- | --- |
| Command-line coordination | `main.py` | Parses options and coordinates the original workflows |
| Configuration | `config.py` | Defines local paths, limits, and platform settings |
| SQLite storage | `core/database.py` | Stores targets and action history |
| Message templates | `core/message_templates.py` | Builds and validates draft text |
| Checkpoints | `core/checkpoint.py` | Saves progress for recovery after interruption |
| Retry handling | `core/retry_logic.py` | Retries selected failures with backoff |
| Rate limiting | `core/rate_limiter.py` | Tracks and limits actions |
| Browser prototype | `core/browser.py` | Configures Selenium and Chrome |
| Platform adapters | `core/platform/` | Contains the original platform-specific behavior |
| Component tests | `tests/test_suite.py` | Exercises core modules without starting a browser |

Some original modules can be reused after review. Modules that automatically discover targets, simulate human behavior, or perform direct platform actions are considered legacy prototype code during the redesign.

## Repository layout

```text
outreach_bot/
|-- main.py
|-- config.py
|-- core/
|-- data/
|   |-- targets.example.csv
|   `-- proxies.example.txt
|-- docs/
|-- tests/
`-- README.md
```

Working data files are intentionally not tracked. Copy an example file when local test data is needed, and never place private contact information in a commit.

## Local setup

The project includes `pyproject.toml`, so it can be installed from a normally named clone such as `outreach-automation`. Editable installation connects the local source directory to Python without copying contact data or other ignored runtime files.

### Windows PowerShell

```powershell
git clone https://github.com/tzar-maung/outreach-automation.git
cd outreach-automation

py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

The direct dependencies and supported Python version are declared in `pyproject.toml`. The project does not yet provide a fully locked dependency set for byte-for-byte reproducible environments.

## Run the component tests

From inside the repository directory in Windows PowerShell:

```powershell
$env:PYTHONUTF8 = "1"
python tests\test_suite.py
```

These tests use temporary files and do not start a browser. Browser-based commands are intentionally omitted from this README while the human-review redesign is incomplete.

## Roadmap

### Milestone 1: Safety and documentation

- [x] Protect local and sensitive files with `.gitignore`
- [x] Replace tracked working data with example files
- [ ] Document the architecture and current limitations
- [x] Add installable project and dependency metadata
- [x] Correct package imports for normally named clones

### Milestone 2: Contact management

- [ ] Define the contact and activity data model
- [ ] Add contact creation, editing, search, and status tracking
- [ ] Add notes and follow-up dates
- [ ] Add safe CSV import and export

### Milestone 3: Human-reviewed drafts

- [ ] Create personalized message drafts
- [ ] Add an edit and approval step
- [ ] Prevent unattended sending
- [ ] Record sending and replies in activity history

### Milestone 4: Approved workflow automation

- [ ] Evaluate supported, authorized sending integrations
- [ ] Require explicit approval before every send action
- [ ] Add consent, opt-out, rate-limit, and audit controls
- [ ] Test the complete approved-send workflow safely

### Milestone 5: Portfolio and production quality

- [ ] Add focused automated tests
- [ ] Improve error handling and validation
- [ ] Add screenshots and a short demonstration
- [ ] Document design decisions and privacy safeguards

## Security and privacy

Never commit:

- `.env` files or credentials
- Real contact or customer information
- Browser profiles or login sessions
- SQLite databases
- Proxy credentials
- Logs, screenshots, or saved page content

If a secret is accidentally committed, removing it in a later commit is not sufficient because Git retains history. Revoke the secret immediately and clean the repository history before making the repository public again.

## AI-assisted development

This project was conceived and directed by the repository owner with assistance from AI coding tools. The redesign emphasizes understanding the architecture, reviewing each change, testing behavior, and documenting technical decisions rather than treating generated code as automatically correct.

## License

No license has been selected yet. Until a license is added, the repository remains publicly viewable but does not grant general permission to copy, modify, or redistribute the code.
