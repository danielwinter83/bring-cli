# bring-cli

CLI for the [Bring!](https://www.getbring.com/) shopping list API.

Thin wrapper around [miaucl/bring-api](https://github.com/miaucl/bring-api) providing a command-line interface for managing Bring! shopping lists.

## Installation

```bash
pip install git+https://github.com/wintermeyer/bring-cli.git
```

## Configuration

Set these environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `BRING_EMAIL` | Yes | Bring! account email |
| `BRING_PASSWORD` | Yes | Bring! account password |
| `BRING_LIST` | For most commands | Default list UUID (run `bring lists` to find it) |

## Usage

```bash
# Show all lists (to find your list UUID)
bring lists

# Show items on the list
bring list

# Add a single item
bring add "Milch"

# Add item with specification
bring add "Äpfel" --spec "2 kg bio"

# Add multiple items at once
bring add "Milch" "Eier" "Butter" "Brot"

# Mark item as purchased
bring complete "Milch"

# Remove item from list
bring remove "Käse"

# JSON output
bring --json list
bring --json lists
```

## License

MIT
