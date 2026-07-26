# Objective Question Generation Benchmark

## Overview

This repository provides an **automated objective question generation system** for evaluating the knowledge mastery of Large Language Models (LLMs). It generates multiple-choice questions from structured domain knowledge, covering five dimensions of LLM knowledge assessment:

- **Knowledge Accuracy (知识准确性)** — whether the knowledge representation is correct
- **Semantic Robustness (语义鲁棒性)** — resistance to noise and interference
- **Condition Sensitivity (条件敏感性)** — whether knowledge depends on specific conditions
- **Inference Reliability (推理可靠性)** — validity of inference chains
- **Semantic Accuracy (语义准确性)** — correctness at the intention level (parallel relations, value domains, etc.)

## Repository Structure

```
├── config/               # Configuration files (API keys, prompts, schemas)
│   └── config_choice.py
├── src/                  # Core source code (31 modules)
│   ├── objective_question_generation.py  # Main orchestrator
│   ├── construct_question.py             # Question assembly
│   ├── call_LLM.py                       # LLM API wrapper
│   ├── log_manager.py                    # Logging system
│   ├── make_json.py                      # JSON builder
│   ├── stack.py                          # Stub center for external dependencies
│   ├── acc_*.py                          # Knowledge accuracy components
│   ├── rob_*.py                          # Semantic robustness components
│   ├── lim_*.py                          # Condition sensitivity components
│   ├── inf_*.py                          # Inference reliability components
│   ├── att_*.py                          # Semantic accuracy components
│   └── rely_*.py                         # Dependency check wrappers
├── test/                 # Unit tests
│   ├── unit_test.py                      # Test runner
│   ├── unittest_3_xx.py                  # Component-specific test suites
│   ├── input/                            # Test input data (domain knowledge JSON)
│   └── expect/                           # Expected output schemas
└── mutation_test/        # Mutation testing (based on Cosmic-Ray)
    ├── muttest.py                        # Mutation test runner
    ├── muttest_3_xx.py                   # Per-component mutation tests
    ├── mut_config/                       # Cosmic-Ray configuration files
    ├── references/                       # Helper classes for mutation DB
    ├── mut_db/                           # Mutation test results (SQLite)
    └── output/                           # Mutation test reports (HTML)
```

> **Note:** This repository contains the **source code and test infrastructure** only.  
> The original `document/` directory (domain knowledge data files), `choice/` (generated options), and `question/` (generated questions) are **not included** in this public release. See below for their format descriptions if you wish to construct your own domain knowledge.

## Data File Formats (for Reference)

To use this system, you need to create the following data files. Their formats are described below for reference:

### 1. Catalog File (`catalog.csv`)

Defines the knowledge catalog structure. Each row specifies a category name and its ID range.

| Column | Description | Example |
|--------|-------------|---------|
| `catalog` | Category name | `目录列1` |
| `start` | Start ID (inclusive) | `103100` |
| `end` | End ID (exclusive) | `103200` |

### 2. Unit Conversion Table (`unit_conversion_table.csv`)

Defines conversion ratios between units and their base SI unit.

| Column | Description | Example |
|--------|-------------|---------|
| `unit` | Unit symbol | `Ω` |
| `type` | Physical type | `resistance` |
| `ratio` | Ratio to base unit | `1000000000` |

### 3. Unit Name Mapping (`transform_unit.csv`)

Maps unit names to their Chinese/English representations.

| Column | Description | Example |
|--------|-------------|---------|
| `单位名称` | Unit name | `欧姆` |
| `单位` | Physical type | `电阻` |
| `单位表示` | Representation type | `中文简称` |

### 4. Unit Irrationality Table (`unit_irrationality_table.csv`)

Defines physical limits for units (e.g., absolute zero for temperature).

| Column | Description | Example |
|--------|-------------|---------|
| `unit` | Unit symbol | `℃` |
| `compare` | Comparison operator | `belowequal` |
| `index` | Limit value | `-273.15` |

### 5. Stop Words (`stopwords.txt`)

One word per line. Used by the stop words interference component.

### 6. Chinese Characters (`all_3500_chars.txt`)

One character per line, covering 3500 common Chinese characters. Used for homophone substitution.

## Setup

### Prerequisites

- Python 3.10+
- [DeepSeek API](https://platform.deepseek.com/) key (or compatible OpenAI-API endpoint)

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd <repo-directory>

# Install dependencies
pip install openai jsonschema numpy pandas pypinyin scikit-learn joblib whoosh
```

### Configuration

Set your API key via environment variable:

```bash
# Windows (PowerShell)
$env:DEEPSEEK_API_KEY = "your-api-key-here"

# Linux/Mac
export DEEPSEEK_API_KEY="your-api-key-here"
```

To use a different API endpoint, modify `API_BASE_URL` in `config/config_choice.py`.

## Usage

### Run Unit Tests

```bash
python -m pytest test/
```

Or run a specific test:

```bash
python test/unittest_3_04.py
```

### Generate Questions

1. Prepare your domain knowledge data files in the format described above.
2. Run the main orchestrator:

```bash
python -m src.objective_question_generation
```

### Run Mutation Tests

```bash
python mutation_test/muttest.py
```

## Attribution

This codebase is a **redacted public release** derived from a research project. 
- All proprietary domain knowledge and project-specific identifiers have been removed.
- The algorithmic framework and test infrastructure are released as-is for research purposes.
- The original `document/`, `choice/`, and `question/` directories are omitted; users must supply their own domain knowledge.

## License

This project is provided for academic and research purposes.
