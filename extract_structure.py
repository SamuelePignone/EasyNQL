from sqlalchemy import create_engine, MetaData
from sqlalchemy.schema import CheckConstraint

import sys

def extract_schema(database_url, output_file):
    # Create the engine
    engine = create_engine(database_url)
    metadata = MetaData()
    
    # Reflect the database schema
    metadata.reflect(bind=engine)
    
    with open(output_file, 'w') as f:
        for table_name, table in metadata.tables.items():
            f.write(f"Table: {table_name}\n")
            for column in table.columns:
                col_name = column.name
                col_type = str(column.type)
                constraints = []
                if not column.nullable:
                    constraints.append("NOT NULL")
                if column.primary_key:
                    constraints.append("PRIMARY KEY")
                if column.unique:
                    constraints.append("UNIQUE")
                if column.default is not None:
                    default_value = column.default.arg
                    if callable(default_value):
                        default_value = default_value(None)
                    constraints.append(f"DEFAULT {default_value}")
                # ForeignKey constraints
                for fk in column.foreign_keys:
                    constraints.append(f"FOREIGN KEY -> {fk.target_fullname}")
                constraints_str = " ".join(constraints)
                f.write(f"- {col_name} ({col_type} {constraints_str})\n")
                for index in table.indexes:
                    index_columns = ', '.join([col.name for col in index.columns])
                    f.write(f"Index: {index.name} on columns ({index_columns})\n")
                for constraint in table.constraints:
                    if isinstance(constraint, CheckConstraint):
                        f.write(f"Check Constraint: {constraint.sqltext}\n")
            f.write("\n")
    print(f"Database schema has been written to {output_file}")

if __name__ == "__main__":
    # Example database URLs:
    # SQLite: 'sqlite:///your_database.db'
    # PostgreSQL: 'postgresql://user:password@localhost:5432/your_database'
    # MySQL: 'mysql+pymysql://user:password@localhost:3306/your_database'
    if len(sys.argv) != 3:
        print("Usage: python extract_schema.py <database_url> <output_file>")
        sys.exit(1)
    database_url = sys.argv[1]
    output_file = sys.argv[2]
    extract_schema(database_url, output_file)