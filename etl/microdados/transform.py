import json
import logging
import os
import warnings
from datetime import datetime
from shutil import rmtree

import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(name="microdados - transform")

warnings.filterwarnings("ignore")


def load_dataframe(year: int) -> pd.DataFrame:
    return pd.read_csv(
        f"./data/raw/microdados/{year}.csv",
        delimiter=";",
        encoding="latin1",
        low_memory=False,
    )


def transform_date_columns(df: pd.DataFrame) -> pd.DataFrame:
    date_columns = [column for column in df.columns if column.startswith("DT")]
    for column in date_columns:
        df[column] = df[column]. \
            apply(
            lambda date:
            datetime.strptime(date, "%d%b%Y:%H:%M:%S")
            if isinstance(date, str) and date != "0"
            else None
        )
    return df


def transform_boolean_columns(df: pd.DataFrame) -> pd.DataFrame:
    boolean_columns = [column for column in df.columns
                       if column.startswith("IN")]
    df[boolean_columns] = df[boolean_columns]. \
        replace(to_replace=9.0, value=None). \
        astype("bool")
    return df


def transform_integer_columns(df: pd.DataFrame) -> pd.DataFrame:
    integer_columns = [column for column in df.columns
                       if column.startswith("QT")]
    df[integer_columns] = df[integer_columns]. \
        fillna(0). \
        astype("int32")

    df["NU_ANO_CENSO"] = df["NU_ANO_CENSO"]. \
        astype("int16")

    return df


def transform_categorical_columns(df: pd.DataFrame) -> pd.DataFrame:
    categorical_columns = [column for column in df.columns if column.startswith("TP")] + [
        "CO_LINGUA_INDIGENA_1", "CO_LINGUA_INDIGENA_2", "CO_LINGUA_INDIGENA_3"
    ]
    with open("./etl/microdados/transform/map_categorical_columns.json") as file:
        map_categorical_columns = json.load(file)

    if columns_not_mapped := set(categorical_columns).difference(
            map_categorical_columns.keys()):
        raise Exception(f"Columns not mapped: {columns_not_mapped}")
    df[categorical_columns] = df[categorical_columns]. \
        astype("float"). \
        fillna(-1). \
        astype("int"). \
        astype("str")
    for column in categorical_columns:
        df[column] = df[column]. \
            replace(to_replace=map_categorical_columns[column])
    df[categorical_columns] = df[categorical_columns].replace(["-1", "9"], None)
    return df


def transform_identifier_columns(df: pd.DataFrame) -> pd.DataFrame:
    identifier_columns = ["NU_DDD", "NU_TELEFONE", "NU_CNPJ_ESCOLA_PRIVADA",
                          "NU_CNPJ_MANTENEDORA", "CO_ESCOLA_SEDE_VINCULADA", "CO_IES_OFERTANTE",
                          "CO_DISTRITO", "CO_CEP"]
    df[identifier_columns] = df[identifier_columns].astype("str")

    identifier_columns_int = ["CO_REGIAO", "CO_UF", "CO_MESORREGIAO", "CO_MICRORREGIAO", "CO_MUNICIPIO"]
    df[identifier_columns_int] = df[identifier_columns_int].astype("int32")

    df["CO_ENTIDADE"] = df["CO_ENTIDADE"].astype("int64")
    return df


def create_new_columns(df: pd.DataFrame) -> pd.DataFrame:
    df["NO_PAIS"] = "Brasil"
    return df


def save_dataframe(df: pd.DataFrame) -> None:
    df.to_parquet(
        "./data/transformed/microdados.parquet",
        engine="pyarrow",
        compression="snappy",
        index=None,
        partition_cols=["NU_ANO_CENSO"]
    )


def main() -> None:
    folder = "./data/transformed/microdados.parquet"
    if os.path.exists(folder):
        logger.debug(f"Overwriting {folder}")
        rmtree(folder)
    for year in range(2016, 2023):
        logger.info(year)
        df = load_dataframe(year)
        df = transform_integer_columns(df)
        df = transform_identifier_columns(df)
        df = transform_categorical_columns(df)
        df = transform_date_columns(df)
        df = transform_boolean_columns(df)
        df = create_new_columns(df)
        save_dataframe(df)


if __name__ == "__main__":
    main()
