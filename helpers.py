import asyncio
import async_timeout
import aiohttp
import random
import aiofiles
import json
import re
import pymongo
import logging


logging.basicConfig(filename="app.log", level=logging.INFO)


def open_save_file(path, mode, data_string=None, callback=None):
    """
    CRUD string to files, return data_string, readlines result as string or callback(params).
    """
    with open(path, mode=mode, encoding="utf-8") as f:
        output = ""
        if mode is "r":
            output = f.read()
        elif mode is "w":
            f.write(data_string)
            output = data_string
        f.close()
        if callback is None:
            return output
        else:
            return callback(output)


@DeprecationWarning
async def bound_fetch(sem, session, url, method="GET", postdata="",  **headers):
    async with sem:
        await fetch(session, url, method, postdata, **headers)


async def fetch(session, url, method="GET", postdata="",  **headers):
    try:
        if headers is None:
            headers = {}
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:51.0) Gecko/20100101 Firefox/51.0"
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        headers["Accept-Language"] = "en-US,en;q=0.5"
        with async_timeout.timeout(30):
            if method == "GET" and postdata != "":
                async with session.request(method, url, headers=headers, params=postdata) as response:
                    # print(response.request_info.url)
                    return await response.text()
            else:
                async with session.request(method, url, headers=headers, data=postdata) as response:
                    return await response.text()
    except Exception as e:
        logging.error("Error: {}\nArgs: {}".format(str(e), e.args))
        # TODO: might change this.
        return "Error"


def parse_reddit_url(url):
    segments = url.split("/")
    if len(segments) is not 7:
        logging.error("Invalid sub-reddit url: {}".format(url))
    return {
        "id": segments[4],
        "sub-reddit": segments[2],
        "safe_title": segments[5]
    }