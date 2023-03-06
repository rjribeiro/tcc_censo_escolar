import os
from glob import glob
from time import sleep
from zipfile import ZipFile, BadZipfile
import subprocess
import logging

import requests
import backoff

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("etl - microdados")

@backoff.on_exception(
    backoff.expo,
    requests.exceptions.RequestException
)
def make_request(url: str) -> None:
    with requests.get(url, stream=True, verify=False) as r:
        r.raise_for_status()
        with open(f"./data/raw/microdados/zips/{year}.zip", 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


def test_zip(year: int) -> None:
    ZipFile(f"./data/raw/microdados/zips/{year}.zip", 'r')


def download_file(year: int) -> None:
    url = f"https://download.inep.gov.br/dados_abertos/microdados_censo_escolar_{year}.zip"
    logger.info(f"Downloading {url}")
    try:
        make_request(url)
        test_zip(year)
    except (requests.exceptions.ChunkedEncodingError, BadZipfile) as e:
        sleep(100)
        try:
            if f"./data/raw/microdados/zips/{year}.zip" in os.listdir():
                os.remove(f"{year}.zip")
            make_request(url)
            test_zip(year)
        except Exception as e:
            raise Exception(f"Download error: {e}") from e
    except Exception as e:
        raise Exception(f"Download error: {e}") from e

    logger.debug("Download complete")


def unzip_file(year: int) -> None:
    logger.debug("Unzipping")
    with ZipFile(f"./data/raw/microdados/zips/{year}.zip", 'r') as zip:
        zip.extractall("data/raw/microdados")

    recursive_zips = [file for file in glob(f"*{year}/DADOS/*")
                       if ".rar" in file or ".zip" in file]
    for recursive_zip_name in recursive_zips:
        subprocess.run(["unar", "-o", f"./data/raw/microdados/{year}/DADOS", year])
        os.remove(f"{recursive_zip_name}")

    logger.debug("Unzip complete")


if __name__ == "__main__":
    for year in range(2016, 2022):
        download_file(year)
        unzip_file(year)