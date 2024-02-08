# Functions
def create_message(table_name, query):
    class message:
        def __init__(message, system, user, column_names, column_attr):
            message.system = system
            message.user = user
            message.column_names = column_names
            message.column_attr = column_attr

    system_template = """

    The following data is about the forcasted CO2 emission starts at {} untill the remaining of today, your job is to explain it simply to the user akin to a weather commentator, \n

    CO2 values are: {} \n
    """

    user_template = "Write a SQL query that returns - {}"

    tbl_describe = duckdb.sql("DESCRIBE SELECT * FROM " + table_name + ";")
    col_attr = tbl_describe.df()[["column_name", "column_type"]]
    col_attr["column_joint"] = col_attr["column_name"] + " " + col_attr["column_type"]
    col_names = (
        str(list(col_attr["column_joint"].values))
        .replace("[", "")
        .replace("]", "")
        .replace("'", "")
    )

    system = system_template.format(table_name, col_names)
    user = user_template.format(query)

    m = message(
        system=system,
        user=user,
        column_names=col_attr["column_name"],
        column_attr=col_attr["column_type"],
    )
    return m


def add_quotes(query, col_names):
    for i in col_names:
        if i in query:
            query = str(query).replace(i, '"' + i + '"')
    return query


# Set the query

query = "How many cases ended up with arrest?"
msg = create_message(table_name="chicago_crime", query=query)


m = create_message(table_name="chicago_crime", query=query)

messages = [
    {"role": "system", "content": m.system},
    {"role": "user", "content": m.user},
]

print(messages)
