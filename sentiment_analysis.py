#!/usr/bin/env python
import asyncio
import async_timeout
import aiohttp
import json
import re
import helpers

from pymongo import MongoClient
from time import sleep


async def queue_analyze_data(session, results, apis):
    for sub_reddit in results:
        for post_comment in sub_reddit:
            if helpers.exist_key_database(post_comment["_id"]):
                return
            post_comment["analyzes"] = []
            for _try in range(0, 10):
                for field in post_comment["fields"]:
                    data_api = await analyze_data(session, post_comment[field], apis)
                    if [data for data in data_api if "Error" in data]:
                        continue
                    post_comment["analyzes"].append(data_api)
                helpers.save_database(post_comment)


async def analyze_data(session, data_string, apis):
    analyzed = []
    for api in apis:
        for k, v in api["json_data"].items():
            if v == "data_string":
                api["json_data"][k] = data_string
        analyzed.append({"api": api["name"], "data": helpers.is_json(await helpers.fetch(session, api["url"], api["method"], api["json_data"], **api["headers"]))})
    return analyzed


async def scrap_comments(session, subreddit, apis, keywords):
    try:
        subreddit_dict = helpers.parse_reddit_url(subreddit)
        if not subreddit_dict:
            return []
        reddit_api_response = await helpers.fetch(session, "https://www.reddit.com/r/{}/comments/{}.json?".format(subreddit_dict["sub-reddit"], subreddit_dict["id"]))
        if reddit_api_response == "Error":
            return []
        json_dict = json.loads(reddit_api_response)

        results = []
        for data in json_dict:
            for children in data["data"]["children"]:
                fields = helpers.has_keyword(children["data"], [
                    "title", "body", "selftext"], keywords)
                if fields:
                    saved_data = {}
                    for field in fields:
                        saved_data[field] = children["data"][field]
                    saved_data["_id"] = children["data"]["id"]
                    saved_data["permalink"] = children["data"]["permalink"]
                    saved_data["ups"] = children["data"]["ups"]
                    saved_data["downs"] = children["data"]["downs"]
                    saved_data["score"] = children["data"]["score"]
                    saved_data["author"] = children["data"]["author"]
                    saved_data["created_utc"] = children["data"]["created_utc"]
                    saved_data["fields"] = fields
                    results.append(saved_data)
        return results
    except Exception as e:
        helpers.log_error("Error: {}/nArgs: {}".format(str(e), e.args))
        return "Error"


async def get_new_subs(session, after=None):
    url = "https://www.reddit.com/r/all/new/"
    if after:
        url = "https://www.reddit.com/r/all/new/?count=25&after={}".format(
            after)
    dom = await helpers.fetch(session, url)
    if not dom:
        return "Out of data !"
    return re.findall("data-inbound-url=\"(.*?)\" ", dom, re.DOTALL)


async def queue():
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:

        matches = []
        tasks = []
        last_id = None
        apis = json.loads(helpers.open_save_file("./api.json", "r"))
        keywords = json.loads(helpers.open_save_file("./keyword.json", "r"))

        while True:
            if not matches:
                matches = await get_new_subs(session, last_id)
                if matches == "Out of data !":
                    return
                last_id = matches[len(matches) - 1]
            while matches:
                match = matches.pop()
                task = asyncio.ensure_future(
                    scrap_comments(session, match, apis, keywords))
                tasks.append(task)
            results = [result for result in await asyncio.gather(*tasks) if result and result is not "Error"]
            if results:
                await queue_analyze_data(session, results, apis)


def main():
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(queue())
    loop.run_until_complete(future)


if __name__ == '__main__':
    main()
