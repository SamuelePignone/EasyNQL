# EasyNQL (Natural Query Language)

EasyNQL is a Python-based tool that transforms natural language questions into SQL queries using Large Language Models (LLMs) via [Ollama](https://ollama.com/). With EasyNQL, you can:

- Generate **SQL SELECT queries** from plain language.
- Optionally **connect to a database** to execute the generated queries and retrieve results.
- **Automate error correction** for queries, thanks to LLM-powered corrections.
- Extract a **database schema** using a dedicated script.

## Features

- **Natural Language to SQL**  
  Convert plain English questions into SQL `SELECT` queries without writing SQL directly.

- **Schema Extraction & Awareness**  
  Use the provided `extract_schema.py` script to generate a schema file from your database. EasyNQL uses this schema to produce accurate queries tailored to the schema’s tables and columns.

- **Automatic Error Correction**  
  If the generated query fails, EasyNQL tries to correct it using the LLM, retrying multiple times if necessary (`max_retries` parameter).

- **Supported Databases**  
  PostgreSQL, MySQL, SQLite (easily extendable to other SQL databases supported by SQLAlchemy).

- **Integration with Ollama**  
  Seamlessly integrates with Ollama to list available models and use them for query generation and correction.

## Requirements

- Python 3.9+  
- [Ollama](https://ollama.com/) installed and configured.  
- SQLAlchemy for database connectivity:
  ```bash
  pip install sqlalchemy
  ```
- A compatible database server and a valid connection URL (e.g., PostgreSQL, MySQL, or SQLite).

## Installation

1. Clone the repository:

```bash
git clone https://github.com/SamuelePignone/EasyNQL.git
cd EasyNQL
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Extract the Database Schema (Optional):
To generate a schema file from an existing database:

```bash
python extract_schema.py <database_url> schema.txt
```
This will create a .txt file describing your database’s tables, columns, and constraints.

4. Configure Ollama model:
The choice of Ollama model can significantly impact the performance and accuracy of the generated SQL queries.
Ensure that the Ollama model you want to use (e.g., qwen2.5-coder:1.5b) is available. Refer to [Ollama’s Library](https://ollama.com/library) to manage models.
Qwen 2.5 coder 1.5b is a good trade-off between performance and resource consumption.

## Usage Examples
1. Generate SQL Only
If you just want to generate SQL from natural language (without executing it), you only need the schema file and the model:

```python
from easy_nql import EasyNQL

# Initialize EasyNQL with the schema file and the model
easy_nql = EasyNQL(db_schema_file="schema.txt", model="qwen2.5-coder:1.5b", logs=True)

# Generate SQL from a natural language question
sql_query = easy_nql.generate_sql("Show me the names of all customers who bought 'Product X'")
print("Generated SQL Query:", sql_query)
```

2. Generating and Executing SQL
If you also want to execute the generated queries and retrieve results:

```python
from easy_nql import EasyNQL

easy_nql = EasyNQL(db_schema_file="schema.txt", model="qwen2.5-coder:1.5b", logs=True)
easy_nql.connect("postgresql://user:password@localhost:5432/mydatabase")

response = easy_nql.chat("List all orders placed in the last 30 days")

print("Generated SQL Query:", response["query"])
print("Results:", response["results"])
print("Execution Time (s):", response["execution_time"])
print("Retries used:", response["retries"])
```

3. Human-Readable Responses 
If you prefer a human-friendly answer instead of raw query results, set `human_response=True`:

```python
response = easy_nql.chat("How many customers have ordered more than 5 times?", human_response=True)

print("Generated SQL Query:", response["query"])
print("Results:", response["result"])
print("Human-friendly Answer:", response["answer"])
print("Execution Time (s):", response["execution_time"])
print("Retries used:", response["retries"])
```

4. Listing Available Models
```python
available_models = easy_nql.list_available_models()
print("Available Models:", available_models)
```

## Extracting the Schema
Use extract_schema.py to generate a schema file. For example:

```bash
python extract_schema.py postgresql://user:password@localhost:5432/mydatabase schema.txt
```
The generated schema.txt can be fed into NQL:

```python
nql = EasyNQL(db_schema_file="schema.txt", model="qwen2.5-coder:1.5b")
```

NQL will then use this schema information to produce SQL queries aligned with your database structure.

## Documentation

### Class `EasyNQL`

Parameters:

- **db_schema** or **db_schema_file**: The source of the database schema to guide SQL generation.
- **model**: The name of the Ollama model to use.
- **database_type**: The type of database (e.g., postgresql, mysql, sqlite).
- **logs**: Boolean indicating whether to enable logging.
- **log_level**: Logging level (e.g., `DEBUG`, `INFO`).
- **log_file**: Path for the log file (if logs are enabled).

Key Methods:

- **connect(database_url: str) -> None**: Connect to the given database.
- **generate_sql(natural_language_question: str) -> str**: Convert a natural language question into a SQL `SELECT` query.
- **chat(natural_language_question: str, max_retries: int = 3, human_response: bool = False) -> dict**: Generate and optionally execute SQL query. If human_response is True, returns a human-friendly answer.
- **list_available_models() -> List[str]**: List all models available in Ollama.

Helper Methods:

- **fix_error_message(error: str, question: str = None, sql_query: str = None) -> str**: Attempt to correct SQL errors using the LLM.
- **generate_human_response(query_results: str, question: str = None) -> str**: Given query results, produce a human-like summary.

## Contributing
Contributions are welcome! If you have suggestions, improvements, or feature requests, please open an issue or submit a pull request.

### Thank you for choosing EasyNQL! 🎉
> Made with ❤️ by [Samuele Pignone](https://github.com/SamuelePignone)