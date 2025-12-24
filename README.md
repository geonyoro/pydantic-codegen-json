# pydantic-model-gen

A Python tool that automatically generates [Pydantic](https://docs.pydantic.dev/) models from JSON data. This utility recursively parses a JSON file and outputs the corresponding Python class definitions, handling nested objects, lists, and type unions.

## Features

- **Recursive Parsing**: Generates detailed models for deeply nested JSON structures.
- **Type Unions**: Automatically detects and handles lists containing mixed types (e.g., `list[str | MyModel]`).
- **Deduplication**: Identifies and reuses identical model definitions to keep the output concise.
- **Interactive Combination**: Optionally prompts to combine similar classes found at the same level in the hierarchy (experimental).
- **Field Aliasing**: Automatically handles fields starting with `_` by aliasing them (e.g., `_id` becomes `id` with an alias).

## Requirements

- Python 3.10+
- [Pydantic](https://pypi.org/project/pydantic/)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/pydantic-model-gen.git
   cd pydantic-model-gen
   ```

2. Install Pydantic:
   ```bash
   pip install pydantic
   ```

## Usage

Run the script by passing the path to your JSON file as an argument. The generated Python code is printed to standard output.

```bash
python pydantic_model_gen/from_json.py path/to/data.json > models.py
```

### Example

Given a `sample.json` file:

```json
{
  "user": {
    "name": "Alice",
    "_id": "12345"
  },
  "tags": ["admin", "editor"]
}
```

Running the tool:

```bash
python pydantic_model_gen/from_json.py sample.json
```

Will generate output similar to:

```python
from pydantic import BaseModel, Field


class UserType(BaseModel):
    name: str
    id: str = Field(alias="_id")


class RootType(BaseModel):
    user: UserType
    tags: list[str]
```

## How It Works

1. **Tree Construction**: Parses the JSON into a node tree (`NDict`, `NList`, `Raw`).
2. **Type Computation**: Recursively determines types for all fields.
3. **Deduplication**: Hashes class bodies to detect and merge duplicate definitions.
4. **Interactive Mode**: If multiple similar classes are detected, the script may prompt to combine them into a single definition.
5. **Output**: Prints the resulting Pydantic models to stdout.