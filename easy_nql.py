from typing import List, Tuple, Optional, Any, Union

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Result
from sqlalchemy.exc import SQLAlchemyError

import logging
import ollama
import time


class EasyNQL:
    """
    A class that converts natural language questions into SQL queries using a specified model and database schema.
    It attempts to execute the generated SQL query against a provided database and handle errors if they occur.
    """

    def __init__(
        self,
        db_schema: str = None,
        db_schema_file: str = None,
        model: str = "qwen2.5-coder:1.5b",
        database_type: str = "",
        logs: bool = False,
        log_level: str = "DEBUG",
        log_file: str = "./out.log"
    ) -> None:
        """
        Initialize the EasyNQL instance.

        :param db_schema: The name of a file (without extension) that contains the database schema text.
        :param db_schema_file: The path to a database schema file.
        :param model: The model to be used by the ollama chat API.
        :param database_type: The type of the database (e.g., "postgresql", "mysql", "sqlite").
        :param logs: Whether to log queries and results.
        :param log_level: The logging level (e.g., "DEBUG", "INFO").
        :param log_file: The path for the log file.
        """
        if db_schema:
            with open(f"{db_schema}.txt", "r", encoding="utf-8") as f:
                self.schema_text = f.read()
        elif db_schema_file:
            with open(db_schema_file, "r", encoding="utf-8") as f:
                self.schema_text = f.read()
        else:
            raise ValueError("Either db_schema or db_schema_file must be provided")

        self.engine: Optional[Engine] = None

        # Retrieve list of available models from ollama
        all_models = list(ollama.list())
        if not all_models or not isinstance(all_models[0], tuple):
            raise ValueError("Could not retrieve available models from ollama.")

        # Extract model names
        self.available_model_names = [m.model for m in all_models[0][1]]

        if model not in self.available_model_names:
            raise ValueError(f"Invalid model. Available models: {self.available_model_names}")

        self.model = model
        self.database_type = database_type
        self.logs = logs
        self.natural_language_question: Optional[str] = None
        self.generated_query: Optional[str] = None

        # Logging configuration (enabled only if self.logs is True)
        self.logger = logging.getLogger(__name__)
        if self.logs:
            numeric_level = getattr(logging, log_level.upper(), logging.DEBUG)
            logging.basicConfig(
                filename=log_file,
                level=numeric_level,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

    def connect(self, database_url: str) -> None:
        """
        Connect to the specified database using SQLAlchemy.

        :param database_url: The database URL.
        """
        self.engine = create_engine(database_url)
        self.database_type = self.get_database_type(database_url)
        self._log(f"Connected to database: {database_url}", level="info")

    @staticmethod
    def get_database_type(database_url: str) -> str:
        """
        Determine the database type from the URL.

        :param database_url: The database connection URL.
        :return: The database type as a string.
        """
        if "postgresql" in database_url:
            return "postgresql"
        elif "mysql" in database_url:
            return "mysql"
        elif "sqlite" in database_url:
            return "sqlite"
        return "unknown"

    def list_available_models(self) -> List[str]:
        """
        List the available models from the Ollama service.

        :return: A list of available model names.
        """
        return self.available_model_names

    def generate_sql(self, natural_language_question: str) -> str:
        """
        Generate an SQL query from a natural language question using the specified model.

        :param natural_language_question: The natural language question to convert.
        :return: The generated SQL query string.
        :raises ValueError: If a non-SELECT query is generated.
        """
        self.natural_language_question = natural_language_question

        # System message to the LLM
        system_prompt = f"""
        You are an expert SQL assistant{f", specialized in {self.database_type}" if self.database_type else ""}. Convert natural language questions into SQL queries based on the provided database schema. Only provide the SQL query without explanations.
        If the natural language question asks you to update, delete, or insert data, please ignore it.
        """.strip()

        # User message to the LLM
        user_prompt = f"""
        Today is: 
        {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}

        Database Schema:
        {self.schema_text}

        Question:
        "{natural_language_question}"
        """.strip()

        response: ollama.ChatResponse = ollama.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
        )

        self.generated_query = response.message.content
        clear_response = self._clear_llm_response(self.generated_query)
        safe_query = self._is_safe_query(clear_response)
        self._log(f"Generated SQL: {safe_query}", level="debug")
        return safe_query

    def fix_error_message(self, error: str, question: str = None, sql_query: str = None) -> str:
        """
        Attempt to fix SQL query errors by asking the model to correct the query.

        :param error: The error message returned by the database.
        :param question: The original natural language question.
        :param sql_query: The SQL query that caused the error.
        :return: The fixed SQL query.
        :raises ValueError: If a non-SELECT query is generated.
        """
        if not sql_query:
            if not self.generated_query:
                raise ValueError("The sql_query parameter must be provided or a SQL query must be generated first.")
            sql_query = self.generated_query

        if not question:
            if not self.natural_language_question:
                raise ValueError("The question parameter must be provided or a natural language question must be generated first.")
            question = self.natural_language_question

        system_prompt = f"""
        You are an expert SQL assistant{f", specialized in {self.database_type}" if self.database_type else ""}. Try to fix the error in the SQL query based on the provided database schema. Only provide the SQL query without explanations. Don't write anything more than the fixed query.
        """.strip()

        user_prompt = f"""
        Today is: 
        {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}

        Database Schema:
        {self.schema_text}

        Question:
        "{question}"

        Error:
        {error}

        SQL Query:
        {sql_query}
        """.strip()

        response: ollama.ChatResponse = ollama.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
        )

        content = response.message.content
        clear_response = self._clear_llm_response(content)
        fixed_query = self._is_safe_query(clear_response)
        self._log(f"Fixed SQL: {fixed_query}", level="debug")
        return fixed_query

    def chat(
            self, 
            natural_language_question: str, 
            max_retries: int = 3, 
            human_response: bool = False
        ) -> dict:
        """
        Given a natural language question, generate and execute an SQL query, retrying up to 3 times if errors occur.

        :param natural_language_question: The natural language question.
        :param max_retries: The maximum number of retries in case of errors.
        :param human_response: Whether to return a human-readable response.
        :return: A dictionary containing the query, results, the answer (if human_response is True), execution time, and retries used.
        :raises ValueError: If the SQL query cannot be executed after the maximum number of retries.
        """
        start_time = time.time()
        try:
            sql_query = self.generate_sql(natural_language_question)
        except ValueError:
            raise ValueError("Failed to generate a valid SQL query from the natural language question.")

        error = None
        rows, column_names = None, None
        count_tries = 0

        # Attempt to execute & fix query up to `max_retries` times
        while count_tries < max_retries:
            rows, column_names, error = self._execute_sql_query(sql_query)
            if error:
                self._log(f"Query failed (attempt {count_tries+1}): {error}", level="warning")
                try:
                    sql_query = self.fix_error_message(error)
                except ValueError as e:
                    self._log(f"Failed to fix query: {str(e)}", level="error")
                    break
                count_tries += 1
            else:
                break

        if count_tries == max_retries and error:
            err_msg = (
                f"The SQL query could not be executed after {max_retries} attempts.\n"
                f"Last generated query:\n{sql_query}\n\nError:\n{error}"
            )
            self._log(err_msg, level="error")
            raise ValueError(err_msg)

        execution_time = round(time.time() - start_time, 2)
        query_results = self._format_results(rows, column_names)

        # Logging final execution details
        self._log(f"Natural Language Question: {natural_language_question}", level="info")
        self._log(f"Final SQL Query: {sql_query}", level="info")
        self._log(f"Retries used: {count_tries}", level="info")
        self._log(f"Execution Time: {execution_time} seconds", level="info")

        if human_response:
            answer = self.generate_human_response(str(query_results))
            return {
                "query": sql_query, 
                "result": query_results, 
                "answer": answer,
                "execution_time": execution_time,
                "retries": count_tries
            }

        return {
            "query": sql_query, 
            "results": query_results,
            "execution_time": execution_time,
            "retries": count_tries
        }

    def generate_human_response(self, query_results: str, question: str = None) -> str:
        """
        Generate a human-like response to the original question, given the query results.

        :param query_results: The query results as a string.
        :param question: The original natural language question.
        :return: A human-friendly answer.
        :raises ValueError: If the natural language question is not provided.
        """
        if not question:
            if not self.natural_language_question:
                raise ValueError(
                    "The natural_language_question parameter must be provided or a question must be generated first."
                )
            question = self.natural_language_question

        system_prompt = f"""
        You are an expert SQL assistant{f", specialized in {self.database_type}" if self.database_type else ""}. Generate a response to the question based on the provided database schema and query results. Be concise and provide a short answer in a human-like phrase.
        """.strip()

        user_prompt = f"""
        Database Schema:
        {self.schema_text}

        Question:
        "{question}"

        The executed query is:
        {self.generated_query}

        Query Results:
        {query_results}
        """.strip()

        response: ollama.ChatResponse = ollama.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
        )

        return response.message.content

    def _execute_sql_query(self, sql_query: str) -> Tuple[Optional[List[Tuple[Any]]], Optional[List[str]], Optional[str]]:
        """
        Execute the given SQL query and return the results.

        :param sql_query: The SQL query string.
        :return: A tuple (rows, column_names, error).
        """
        if not self.engine:
            return None, None, "No database engine is connected."

        try:
            with self.engine.connect() as connection:
                result: Result = connection.execute(text(sql_query))
                rows = result.fetchall()
                column_names = list(result.keys())
                return rows, column_names, None
        except SQLAlchemyError as e:
            return None, None, str(e)
        except Exception as e:
            return None, None, str(e)

    @staticmethod
    def _format_results(rows: Optional[List[Tuple[Any]]], column_names: Optional[List[str]]) -> Union[str, List[dict]]:
        """
        Format the result set into a list of dictionaries where keys are column names.

        :param rows: The fetched rows.
        :param column_names: The list of column names.
        :return: A list of dictionaries representing the rows, or a string if no results.
        """
        if not rows or not column_names:
            return "No results found."

        result_list = []
        for row in rows:
            row_data = {column_names[i]: row[i] for i in range(len(column_names))}
            result_list.append(row_data)
        return result_list

    @staticmethod
    def _clear_llm_response(response: str) -> str:
        """
        Clean the response from the LLM by removing code block markers and other extraneous characters.

        :param response: The response text from the LLM.
        :return: Cleaned response text.
        """
        response = response.replace(">>>", "")
        lines = [line for line in response.split("\n") if not line.startswith("```")]
        return "\n".join(lines)

    def _is_safe_query(self, query: str) -> str:
        """
        Ensure that the generated query is a SELECT query.

        :param query: The SQL query string.
        :return: The verified SQL query string.
        :raises ValueError: If the query does not start with SELECT.
        """
        query = query.split(";")[0]
        if query.strip().upper().startswith("SELECT"):
            return query.strip()
        self._log(f"Query is not a SELECT statement: {query}", level="error")
        raise ValueError("A non-SELECT query was generated. Please try again.")

    def _log(self, message: str, level: str = "debug") -> None:
        """
        Log a message to both the console (with color) and to the file if logging is enabled.

        :param message: The log message.
        :param level: The logging level ("info", "warning", "error", "debug").
        """
        if not self.logs:
            return
        log_methods = {
            "info": self.logger.info,
            "warning": self.logger.warning,
            "error": self.logger.error,
            "debug": self.logger.debug
        }
        log_method = log_methods.get(level, self.logger.debug)
        log_method(message)

        colors = {
            "info": "\033[94m",
            "warning": "\033[93m",
            "error": "\033[91m",
            "debug": "\033[0m",
            "end": "\033[0m"
        }
        color = colors.get(level, colors["debug"])
        print(f"{color}{message}{colors['end']}")

    def __str__(self) -> str:
        return (
            f"EasyNQL Object: model={self.model}, "
            f"database_type={self.database_type if self.database_type else 'None'}, "
            f"logs={self.logs}"
        )

    def __del__(self) -> None:
        if self.engine:
            self.engine.dispose()
            self._log("Database engine disposed", level="info")
        else:
            self._log("No database engine to dispose", level="info")
