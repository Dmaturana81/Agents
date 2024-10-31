

``` python
class Connection(OpenAISchema):
    """Class that manage the connection to the database, Some base methods to bring description information, and other to execute queries"""

    sql_warehouse_id: str 
    instance: str 
    uri_sql_endpoint: str | None = None
    uri_sql_history: str | None = None
    catalog: str
    database: str
    token: str

    @model_validator(mode='before')
    @classmethod
    def connect(cls, values):
        values['uri_sql_endpoint'] = "https://{instance}/api/2.0/sql/statements/".format(instance=values['instance'])
        values['uri_sql_history'] = "https://{instance}/api/2.0/sql/history/queries".format(instance=values['instance'])
        return values

    def generate_headers(self) -> Dict[str, str]:
        """Method to generate the headers for the connection"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def generate_data_post(
        self,
        query_to_execute: str,
        fmt: Literal["CSV", "ARROW_STREAM", "JSON_ARRAY"] = "JSON_ARRAY",
        disposition: Literal["INLINE", "diff"] = "INLINE",
    ) -> Dict[str, str]:
        """Method that generate the body of the post request to execute the query in the SQL Warehouse"""
        data = {
            "warehouse_id": f"{self.sql_warehouse_id}",
            "format": fmt,  # for big use CSV, ARROW_STREAM, JSON_ARRAY is default for small <25mb
            "disposition": disposition,  # for big security attention with token here, needs to be diff, INLINE is default
            "statement": query_to_execute, # query to execute
            "catalog": f"{self.catalog}.{self.database}", # catalog and database to use
            "wait_timeout": "0s",
        }
        return data

    @classmethod
    def parse_result(cls, data: Dict) -> Dict[str, Any]:
        """Class method to parse the result into a dataframe compatible format
        Args:
            data (Dict): data from the SQL Warehouse
        Returns:
            Dict: dictionary with columns and data
        """
        columns = [x["name"] for x in data["manifest"]["schema"]["columns"]]
        results = data["result"]["data_array"]
        return {"columns": columns, "data": results}

#| exports
@patch
def get_tables(
            self:'Connection'
        ) -> List[str]:
    """Method to list tables available in the database
    Returns:
        List[str]: list of tables names
    """
    query = f"SHOW TABLES in {self.catalog}.{self.database}"
    data = self.execute_query(query)
    tables = data["data"]  # self.parse_result(data)['data']
    return [f"{self.catalog}.{x[0]}.{x[1]}" for x in tables if x[1].find("payload") == -1]
#| export
@patch
def get_table_columns(
        self:'Connection',
        table: str
    ) -> List[str]:
    """Method to get the columns of a table
    Args:
        table (str): table name
    Returns:
        List[str]: list of columns
    """
    query = f"DESCRIBE TABLE {table}"
    data = self.execute_query(query)
    return [x[0] for x in data["data"]]  # self.parse_result(data)['data']]


#| export
@patch
def get_tables_columns(
        self:'Connection', 
    ) -> Dict[str, List[str]]:
    """
    Method to get the tables and columns
    Returns:
        Dict[str, List[str]]: dictionary with table name as key and list of columns
    """
    tables = self.get_tables()
    tables_columns = {}
    for table in tables:
        table_columns = self.get_table_columns(table)
        tables_columns[table] = table_columns
    return tables_columns
    

#| export
@classmethod
@patch
def row_2_str(
        cls:'Connection',
        row
    ):
    """Method to convert a column from the table description into a string, spcifying the name, type and comment availables
    Args:
        row: row to convert
    Returns:
        str: row as string
    """
    return f"{row[0]} ( {row[1] if row[1] else ''} {row[2] if row[2] else ''})"

#| export
@classmethod
@patch
def list_cols(
        cls:'Connection',
        df
    ):
    """Method to list the columns of a table
    Args:
        df: dataframe with the columns
    Returns:
        List[str]: list of columns as string
    """
    end_i = df.loc[df['col_name'] == ''].index[0]
    cols = df.loc[:end_i-1] #usar i -1
    return cols.apply(lambda row: cls.row_2_str(row), axis=1).to_list()


#| export
@patch
def get_table_description(
        self:'Connection', 
        table: str
    ) -> Dict[str, str]:
    """Method that returns the table description from Databricks
    Args:
        table (str): table name
    Returns:
        Dict[str, str]: dictionary with table and description
    """
    query = f"DESCRIBE TABLE EXTENDED {table}"
    data = self.execute_query(query)
    df = pd.DataFrame(data['data'], columns = data['columns'])
    cols = self.list_cols(df)
    comment =  df.loc[df['col_name'] == 'Comment']['data_type'].values[0]
    return {"table": table, "description": comment, "columns":cols}  # data #self.parse_result(data)

#| export
@patch
def get_tables_descriptions(
        self:'Connection',
        tables: list[str] | None = None
    ) -> List[Dict[str, str]]:
    """Function that return the tables and the description
    Args:
        tables (list[str], optional): list of tables. Defaults to None.
    Returns:
        List[Dict[str, str]]: list of dictionaries with table and description
    """
    tables = tables if tables else self.get_tables()
    tables_description = []
    for table in tables:
        table_desc = self.get_table_description(table)
        tables_description.append(table_desc)
    return tables_description

#| export
@patch
def execute_query(
        self:'Connection', 
        query: str
    ):
    """Method that execute the query in the SQL Warehouse
    Args:
        query (str): query to execute
    Returns:
        Dict: dictionary with the result of the query
    """
    response = requests.post(
        self.uri_sql_endpoint,
        headers=self.generate_headers(),
        data=json.dumps(self.generate_data_post(query)),
    )
    data = response.json()
    while data["status"]["state"] != "SUCCEEDED":
        status = data["status"]["state"] 
        match status:
            case "RUNNING":
                time.sleep(0.5)
                response = requests.get(
                    self.uri_sql_endpoint + data["statement_id"],
                    headers=self.generate_headers(),
                )
                data = response.json()
            case "PENDING":
                time.sleep(0.5)
                response = requests.get(
                    self.uri_sql_endpoint + data["statement_id"],
                    headers=self.generate_headers(),
                )
                data = response.json()
            case "FAILED":
                raise Exception(traceback.format_exc()) # raise the exception and return the traceback as details, this will be use to cirrect the query made by the LLM
    return self.parse_result(data)
def create_con():
        return Connection(token=os.getenv('DATABRICKS_TOKEN'), catalog = "text2sql", database = "default", instance = os.getenv('SQL_INSTANCE'), sql_warehouse_id = os.getenv('SQL_WAREHOUSE_ID'))
con = create_con()
con.get_tables()
```

<!-- WARNING: THIS FILE WAS AUTOGENERATED! DO NOT EDIT! -->
