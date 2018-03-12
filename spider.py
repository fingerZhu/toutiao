# {i.split(":")[0]:i.split(":")[1] for i in a.split("\n")}
from selenium import webdriver
from bs4 import BeautifulSoup
from hashlib import md5
from config import *
from multiprocessing import Pool
import pymongo
import requests
import re
import os
import time

cookies = None
client = pymongo.MongoClient(MONGO_URL, connect=False)
db = client[MONGO_DB]


# 下载cookie
def download_page_cookie():
    browser = webdriver.Chrome()
    browser.get("https://www.toutiao.com")
    with open("cookies.txt", "w") as f:
        f.write(str({i["name"]: i["value"] for i in browser.get_cookies()}))
    browser.close()
    print("下载成功")


# 调用cookie
def get_page_cookie():
    with open("cookies.txt", "r", encoding="utf-8") as f:
        return eval(f.read())


# 按页码获取
def get_page_index(page, keyword):
    time.sleep(1)
    # 参数
    params = {'offset': (page - 1) * 20, 'format': 'json', 'keyword': keyword, 'autoload': 'true', 'count': 20, 'cur_tab': 3, 'from': 'gallery'}
    headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36"}
    r = requests.get("https://www.toutiao.com/search_content/", headers=headers, params=params, cookies=cookies)
    if r.status_code == 200:
        data = r.json()
        if data and "data" in data.keys():
            data = data.get("data")
            for item in data:
                yield item["url"]


# 获取每个组图的所有图片
def get_page_detail(url):
    try:
        r = requests.get("https://www.toutiao.com/a" + re.findall("group/(\d*)/", url, re.S)[0], cookies=cookies)
        if r.status_code != 200:
            return {"title": "请求错误", "count": 0, "url": url}
        soup = BeautifulSoup(r.text, "lxml")
        title = soup.title.string
        data = eval(re.findall('galleryInfo.*?gallery:.*?parse\("(.*?)"\),', r.text, re.S)[0].replace("\\", ""))
        if data and "sub_images" in data.keys():
            data = data.get("sub_images")
            images = [i["url"] for i in data]
            for image in images:
                download_image(image)
            return {
                "title": title,
                "count": len(images),
                "url": url,
                "images": images,
            }
    except:
        print(url)


# 保存到MongoDB
def save_to_mongo(reslut):
    if db[MONGO_TABLE].insert(reslut):
        print("存储MongoDB成功", reslut)
        return True
    return False


# 下载图片
def download_image(url):
    print("正在下载", url)
    r = requests.get(url)
    if r.status_code == 200:
        content = r.content
        file_path = "{0}/{1}.{2}".format(os.getcwd() + "/img", md5(content).hexdigest(), "jpg")
        if not os.path.exists(file_path):
            with open(file_path, "wb") as f:
                f.write(content)


def main(page):
    global cookies
    cookies = get_page_cookie()
    for url in get_page_index(page, KEYWORD):
        result = get_page_detail(url)
        if result:
            save_to_mongo(result)


if __name__ == "__main__":
    # download_page_cookie()
    pool = Pool()
    pool.map(main, list(range(GROUP_START, GROUP_END + 1)))
