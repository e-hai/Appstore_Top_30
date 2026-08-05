"""Fetch Google Play rankings from the official Play Store web pages.

Google does not expose a public top-charts API. The official collection pages
embed the ranked app list as JSON inside AF_initDataCallback script blocks, so
we parse those blocks and keep the order shown by Google as the official rank.
"""

import json
import http.cookiejar
import logging
import random
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from . import config, db

LOGGER = logging.getLogger(__name__)

PLAY_URL = "https://play.google.com/store/apps"

CALLBACK_RE = re.compile(r">AF_initDataCallback[\s\S]*?</script", re.S)
KEY_RE = re.compile(r"key:\s*'(ds:\d+)'")
VALUE_RE = re.compile(r"data:([\s\S]*?), sideChannel: {}}\);</", re.S)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36"
)

# Google Play's list page no longer embeds chart content in the initial HTML.
# The browser fetches it through the internal batchexecute endpoint; keep the
# request body shape used by google-play-scraper so rankings stay official.
BATCH_BODY_TEMPLATE = (
    "f.req=%5B%5B%5B%22vyAe2%22%2C%22%5B%5Bnull%2C%5B%5B8%2C%5B20%2C${num}%5D%5D%2Ctrue%2Cnull%2C%5B64%2C1%2C195%2C71%2C8%2C72%2C9%2C10%2C11%2C139%2C12%2C16%2C145%2C148%2C150%2C151%2C152%2C27%2C30%2C31%2C96%2C32%2C34%2C163%2C100%2C165%2C104%2C169%2C108%2C110%2C113%2C55%2C56%2C57%2C122%5D%2C%5Bnull%2Cnull%2C%5B%5B%5Btrue%5D%2Cnull%2C%5B%5Bnull%2C%5B%5D%5D%5D%2Cnull%2Cnull%2Cnull%2Cnull%2C%5Bnull%2C2%5D%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2C%5B1%5D%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2Cnull%2C%5B1%5D%5D%2C%5Bnull%2C%5B%5Bnull%2C%5B%5D%5D%5D%5D%2C%5Bnull%2C%5B%5Bnull%2C%5B%5D%5D%5D%2Cnull%2C%5Btrue%5D%5D%2C%5Bnull%2C%5B%5Bnull%2C%5B%5D%5D%5D%5D%2Cnull%2Cnull%2Cnull%2Cnull%2C%5B%5B%5Bnull%2C%5B%5D%5D%5D%5D%2C%5B%5B%5Bnull%2C%5B%5D%5D%5D%5D%5D%2C%5B%5B%5B%5B7%2C1%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C31%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C104%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C9%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C8%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C27%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C12%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C65%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C110%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C88%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C11%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C56%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C55%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C96%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C10%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C122%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C72%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C71%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C64%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C113%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C139%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C150%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C169%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C165%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C151%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C163%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C32%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C16%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C108%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B7%2C100%5D%2C%5B%5B1%2C73%2C96%2C103%2C97%2C58%2C50%2C92%2C52%2C112%2C69%2C19%2C31%2C101%2C123%2C74%2C49%2C80%2C38%2C20%2C10%2C14%2C79%2C43%2C42%2C139%5D%5D%5D%2C%5B%5B9%2C1%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C31%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C104%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C9%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C8%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C27%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C12%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C65%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C110%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C88%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C11%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C56%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C55%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C96%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C10%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C122%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C72%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C71%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C64%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C113%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C139%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C150%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C169%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C165%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C151%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C163%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C32%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C16%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C108%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B9%2C100%5D%2C%5B%5B1%2C7%2C9%2C24%2C12%2C31%2C5%2C15%2C27%2C8%2C13%2C10%5D%5D%5D%2C%5B%5B17%2C1%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C31%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C104%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C9%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C8%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C27%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C12%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C65%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C110%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C88%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C11%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C56%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C55%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C96%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C10%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C122%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C72%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C71%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C64%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C113%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C139%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C150%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C169%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C165%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C151%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C163%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C32%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C16%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C108%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B17%2C100%5D%2C%5B%5B1%2C7%2C9%2C25%2C13%2C31%2C5%2C41%2C27%2C8%2C14%2C10%5D%5D%5D%2C%5B%5B10%2C1%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C31%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C104%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C9%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C8%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C27%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C12%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C65%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C110%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C88%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C11%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C56%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C55%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C96%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C10%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C122%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C72%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C71%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C64%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C113%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C139%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C150%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C169%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C165%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C151%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C163%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C32%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C16%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C108%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B10%2C100%5D%2C%5B%5B1%2C7%2C6%2C9%5D%5D%5D%2C%5B%5B1%2C1%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C31%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C104%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C9%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C8%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C27%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C12%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C65%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C110%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C88%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C11%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C56%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C55%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C96%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C10%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C122%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C72%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C71%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C64%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C113%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C139%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C150%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C169%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C165%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C151%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C163%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C32%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C16%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C108%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B1%2C100%5D%2C%5B%5B1%2C5%2C14%2C38%2C19%2C29%2C34%2C4%2C12%2C11%2C6%2C30%2C43%2C40%2C42%2C16%2C10%2C7%5D%5D%5D%2C%5B%5B4%2C1%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C31%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C104%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C9%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C8%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C27%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C12%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C65%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C110%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C88%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C11%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C56%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C55%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C96%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C10%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C122%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C72%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C71%5D%2C%5B%5B1%2C3%5D%5D%5D%2C%5B%5B4%2C64%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C113%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C139%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C150%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C169%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C165%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C151%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C163%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C32%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C16%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C108%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B4%2C100%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B3%2C1%5D%2C%5B%5B1%2C5%2C14%2C4%2C10%2C17%5D%5D%5D%2C%5B%5B3%2C31%5D%2C%5B%5B1%2C5%2C14%2C4%2C10%2C17%5D%5D%5D%2C%5B%5B3%2C104%5D%2C%5B%5B1%2C5%2C14%2C4%2C10%2C17%5D%5D%5D%2C%5B%5B3%2C9%5D%2C%5B%5B1%2C5%2C14%2C4%2C10%2C17%5D%5D%5D%2C%5B%5B3%2C8%5D%2C%5B%5B1%2C5%2C14%2C4%2C10%2C17%5D%5D%5D%2C%5B%5B3%2C27%5D%2C%5B%5B1%2C5%2C14%2C4%2C10%2C17%5D%5D%5D%2C%5B%5B3%2C12%5D%2C%5B%5B1%2C5%2C14%2C4%2C10%2C17%5D%5D%5D%2C%5B%5B3%2C65%5D%2C%5B%5B1%2C5%2C14%2C4%2C10%2C17%5D%5D%5D%2C%5B%5B3%2C110%5D%2C%5B%5B1%2C5%2C14%2C4%2C10%2C17%5D%5D%5D%2C%5B%5B3%2C88%5D%2C%5B%5B1%2C5%2C14%2C4%2C10%2C17%5D%5D%5D%2C%5B%5B3%2C11%5D%2C%5B%5B1%2C5%2C14%2C4%2C10%2C17%5D%5D%5D%2C%5B%5B3%2C56%5D%2C%5B%5B1%2C5%2C14%2C4%2C10%2C17%5D%5D%5D%2C%5B%5B3%2C55%5D%2C%5B%5B1%2C5%2C14%2C4%2C10%2C17%5D%5D%5D%2C%5B%5B3%2C96%5D%2C%5B%5B1%2C5%2C14%2C4%2C10%2C17%5D%5D%5D%2C%5B%5B3%2C10%5D%2C%5B%5B1%2C5%2C14%2C4%2C10%2C17%5D%5D%5D%2C%5B%5B3%2C122%5D%2C%5B%5B1%2C5%2C14%2C4%2C10%2C17%5D%5D%5D%2C%5B%5B3%2C72%5D%2C%5B%5B1%2C5%2C14%2C4%2C10%2C17%5D%5D%5D%2C%5B%5B3%2C71%5D%2C%5B%5B1%2C3%5D%5D%5D%2C%5B%5B3%2C64%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B3%2C113%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B3%2C139%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B3%2C150%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B3%2C169%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B3%2C165%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B3%2C151%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B3%2C163%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B3%2C32%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B3%2C16%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B3%2C108%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B3%2C100%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B2%2C1%5D%2C%5B%5B1%2C5%2C7%2C4%2C13%2C16%2C12%2C18%5D%5D%5D%2C%5B%5B2%2C31%5D%2C%5B%5B1%2C5%2C7%2C4%2C13%2C16%2C12%2C18%5D%5D%5D%2C%5B%5B2%2C104%5D%2C%5B%5B1%2C5%2C7%2C4%2C13%2C16%2C12%2C18%5D%5D%5D%2C%5B%5B2%2C9%5D%2C%5B%5B1%2C5%2C7%2C4%2C13%2C16%2C12%2C18%5D%5D%5D%2C%5B%5B2%2C8%5D%2C%5B%5B1%2C5%2C7%2C4%2C13%2C16%2C12%2C18%5D%5D%5D%2C%5B%5B2%2C27%5D%2C%5B%5B1%2C5%2C7%2C4%2C13%2C16%2C12%2C18%5D%5D%5D%2C%5B%5B2%2C12%5D%2C%5B%5B1%2C5%2C7%2C4%2C13%2C16%2C12%2C18%5D%5D%5D%2C%5B%5B2%2C65%5D%2C%5B%5B1%2C5%2C7%2C4%2C13%2C16%2C12%2C18%5D%5D%5D%2C%5B%5B2%2C110%5D%2C%5B%5B1%2C5%2C7%2C4%2C13%2C16%2C12%2C18%5D%5D%5D%2C%5B%5B2%2C88%5D%2C%5B%5B1%2C5%2C7%2C4%2C13%2C16%2C12%2C18%5D%5D%5D%2C%5B%5B2%2C11%5D%2C%5B%5B1%2C5%2C7%2C4%2C13%2C16%2C12%2C18%5D%5D%5D%2C%5B%5B2%2C56%5D%2C%5B%5B1%2C5%2C7%2C4%2C13%2C16%2C12%2C18%5D%5D%5D%2C%5B%5B2%2C55%5D%2C%5B%5B1%2C5%2C7%2C4%2C13%2C16%2C12%2C18%5D%5D%5D%2C%5B%5B2%2C96%5D%2C%5B%5B1%2C5%2C7%2C4%2C13%2C16%2C12%2C18%5D%5D%5D%2C%5B%5B2%2C10%5D%2C%5B%5B1%2C5%2C7%2C4%2C13%2C16%2C12%2C18%5D%5D%5D%2C%5B%5B2%2C122%5D%2C%5B%5B1%2C5%2C7%2C4%2C13%2C16%2C12%2C18%5D%5D%5D%2C%5B%5B2%2C72%5D%2C%5B%5B1%2C5%2C7%2C4%2C13%2C16%2C12%2C18%5D%5D%5D%2C%5B%5B2%2C71%5D%2C%5B%5B1%2C3%5D%5D%5D%2C%5B%5B2%2C64%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B2%2C113%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B2%2C139%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B2%2C150%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B2%2C169%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B2%2C165%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B2%2C151%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B2%2C163%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B2%2C32%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B2%2C16%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B2%2C108%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%2C%5B%5B2%2C100%5D%2C%5B%5B1%2C3%2C5%2C4%2C7%2C6%2C11%2C19%2C21%2C17%2C15%2C12%2C16%2C20%5D%5D%5D%5D%5D%5D%2Cnull%2Cnull%2C%5B%5B%5B1%2C2%5D%2C%5B10%2C8%2C9%5D%2C%5B%5D%2C%5B%5D%5D%5D%5D%2C%5B2%2C%5C%22${collection}%5C%22%2C%5C%22${category}%5C%22%5D%5D%5D%22%2Cnull%2C%22generic%22%5D%5D%5D&at=AFSRYlx8XZfN8-O-IKASbNBDkB6T%3A1655531200971&"
)

BATCH_ENDPOINT = "https://play.google.com/_/PlayStoreUi/data/batchexecute"
DEFAULT_BUILD_LABEL = "boq_playuiserver_20220612.08_p0"

_BUILD_LABEL: str | None = None
_COUNTRY_SESSIONS: set[str] = set()
_SESSION_LOCK = threading.Lock()
_REQ_ID = 82003
_REQ_ID_LOCK = threading.Lock()
_OPENER: urllib.request.OpenerDirector | None = None
_OPENER_LOCK = threading.Lock()


class FetchError(RuntimeError):
    pass


class PlayRateLimiter:
    """Small global rate limiter shared by Google Play page requests."""

    def __init__(self, requests_per_second: float = config.PLAY_REQUESTS_PER_SECOND) -> None:
        self._interval = 1.0 / requests_per_second
        self._lock = threading.Lock()
        self._next_at = time.monotonic()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait_for = self._next_at - now
            if wait_for > 0:
                time.sleep(wait_for)
            self._next_at = max(now, self._next_at) + self._interval


RATE_LIMITER = PlayRateLimiter()


def _backoff_seconds(attempt: int, exc: Exception) -> float:
    if isinstance(exc, urllib.error.HTTPError) and exc.code in {403, 429, 500, 502, 503, 504}:
        seconds = float(2 ** (attempt + 2))
    else:
        seconds = 1.0 * (2 ** attempt)
    return seconds + random.uniform(0, 0.5)


def _http_get_text(url: str, timeout: int = config.PLAY_FEED_TIMEOUT, retries: int = config.PLAY_FEED_RETRIES) -> str:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            RATE_LIMITER.wait()
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Cache-Control": "no-cache",
                },
            )
            with _get_opener().open(request, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            last_error = exc
            time.sleep(_backoff_seconds(attempt, exc))
    raise FetchError(f"failed to fetch {url}: {last_error}")


def _get_opener() -> urllib.request.OpenerDirector:
    global _OPENER
    if _OPENER is None:
        with _OPENER_LOCK:
            if _OPENER is None:
                jar = http.cookiejar.CookieJar()
                _OPENER = urllib.request.build_opener(
                    urllib.request.HTTPCookieProcessor(jar)
                )
    return _OPENER


def _http_post(url: str, body: str, timeout: int = config.PLAY_FEED_TIMEOUT, retries: int = config.PLAY_FEED_RETRIES) -> str:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            RATE_LIMITER.wait()
            request = urllib.request.Request(
                url,
                data=body.encode("utf-8"),
                method="POST",
                headers={
                    "User-Agent": USER_AGENT,
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                    "Accept": "*/*",
                },
            )
            with _get_opener().open(request, timeout=timeout) as response:
                return response.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            last_error = exc
            time.sleep(_backoff_seconds(attempt, exc))
    raise FetchError(f"failed to post {url}: {last_error}")


def _extract_build_label(html: str) -> str | None:
    match = re.search(r'cfb2h":"([^"]+)"', html)
    return match.group(1) if match else None


def _remember_build_label(html: str) -> None:
    global _BUILD_LABEL
    label = _extract_build_label(html)
    if label:
        _BUILD_LABEL = label


def _next_req_id() -> int:
    global _REQ_ID
    with _REQ_ID_LOCK:
        _REQ_ID += 1
        return _REQ_ID


def _batch_body(num: int, collection: str, category: str) -> str:
    return (
        BATCH_BODY_TEMPLATE.replace("${num}", str(num))
        .replace("${collection}", collection)
        .replace("${category}", category)
    )


def _parse_batch_response(text: str) -> list:
    lines = text.split("\n")
    if len(lines) < 4:
        raise FetchError("unexpected Google Play batchexecute response")
    input_data = json.loads(lines[3])
    payload = json.loads(input_data[0][2])
    return _path_get(payload, [0, 1, 0, 28, 0]) or []


def _batch_fetch(country: str, chart_type: str, category_id: str, top_n: int) -> list:
    global _BUILD_LABEL
    if _BUILD_LABEL is None:
        _BUILD_LABEL = DEFAULT_BUILD_LABEL
    collection = config.PLAY_COLLECTIONS[chart_type]
    batch_category = "APPLICATION" if category_id == "all" else category_id
    body = _batch_body(top_n, collection, batch_category)
    url = (
        f"{BATCH_ENDPOINT}?rpcids=vyAe2&source-path=%2Fstore%2Fapps"
        "&f.sid=-4178618388443751758"
        f"&bl={urllib.parse.quote(_BUILD_LABEL)}"
        "&authuser=0&soc-app=121&soc-platform=1&soc-device=1"
        f"&_reqid={_next_req_id()}&rt=c&hl=en&gl={country}"
    )
    response = _http_post(url, body)
    app_list = _parse_batch_response(response)
    if app_list:
        return app_list
    # The build label may have changed; refresh it once and retry.
    _BUILD_LABEL = None
    html = _http_get_text(chart_url(country, "free", "all"))
    _remember_build_label(html)
    url = re.sub(r"&bl=[^&]+", f"&bl={urllib.parse.quote(_BUILD_LABEL)}", url)
    response = _http_post(url, body)
    return _parse_batch_response(response)


def _ensure_country_session(country: str) -> list:
    """Prime cookies/build label and return an embedded list if Google serves one."""
    if country in _COUNTRY_SESSIONS:
        return []
    with _SESSION_LOCK:
        if country in _COUNTRY_SESSIONS:
            return []
        html = _http_get_text(chart_url(country, "free", "all"))
        _remember_build_label(html)
        app_list = find_app_list(parse_page(html))
        _COUNTRY_SESSIONS.add(country)
        return app_list


def _path_get(node, path: list[int]):
    for key in path:
        if isinstance(node, dict):
            if key not in node:
                return None
            node = node[key]
        elif isinstance(node, list):
            if key >= len(node):
                return None
            node = node[key]
        else:
            return None
    return node


def parse_page(html: str) -> dict:
    """Parse AF_initDataCallback blocks into a dict keyed by ds:*."""
    parsed: dict[str, object] = {}
    for match in CALLBACK_RE.findall(html):
        key_match = KEY_RE.search(match)
        value_match = VALUE_RE.search(match)
        if not key_match or not value_match:
            continue
        raw = value_match.group(1).strip()
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            LOGGER.debug("skipping unparseable callback %s", key_match.group(1))
            continue
        parsed[key_match.group(1)] = value
    return parsed


def _looks_like_app(item) -> bool:
    app_id = _path_get(item, [12, 0])
    title = _path_get(item, [2])
    developer = _path_get(item, [4, 0, 0, 0])
    icon = _path_get(item, [1, 1, 0, 3, 2])
    return (
        isinstance(app_id, str)
        and "." in app_id
        and isinstance(title, str)
        and isinstance(developer, str)
        and isinstance(icon, str)
    )


def _collect_candidate_lists(node, candidates: list[tuple[int, list]]) -> None:
    if isinstance(node, list):
        scored = sum(1 for item in node if _looks_like_app(item))
        if scored >= 3:
            candidates.append((scored, node))
        for child in node:
            _collect_candidate_lists(child, candidates)
    elif isinstance(node, dict):
        for child in node.values():
            _collect_candidate_lists(child, candidates)


def find_app_list(parsed: dict) -> list:
    """Locate the ranked app list embedded in a Play Store collection page."""
    candidates: list[tuple[int, list]] = []
    for value in parsed.values():
        _collect_candidate_lists(value, candidates)
    if not candidates:
        return []
    candidates.sort(key=lambda item: -item[0])
    return candidates[0][1]


def _parse_price(price_text) -> tuple[float | None, str | None]:
    if price_text is None or str(price_text).strip().lower() == "free":
        return 0.0, None
    text = str(price_text)
    match = re.search(r"([0-9][0-9.,]*)", text)
    if not match:
        return None, None
    amount = float(match.group(1).replace(",", ""))
    return amount, None


def _parse_variant_a(item) -> dict | None:
    app_id = _path_get(item, [12, 0])
    title = _path_get(item, [2])
    if not isinstance(app_id, str) or not isinstance(title, str):
        return None
    price_text = _path_get(item, [7, 0, 3, 2, 1, 0, 2])
    currency = _path_get(item, [7, 0, 3, 2, 1, 0, 1])
    price_amount, price_currency = _parse_price(price_text)
    if price_currency is None and isinstance(currency, str):
        price_currency = currency
    return {
        "app_id": app_id,
        "name": title,
        "developer": _path_get(item, [4, 0, 0, 0]),
        "icon_url": _path_get(item, [1, 1, 0, 3, 2]),
        "price_amount": price_amount,
        "currency": price_currency,
        "rating": _path_get(item, [6, 0, 2, 1, 1]),
        "rating_count": None,
    }


def _parse_variant_b(item) -> dict | None:
    app_id = _path_get(item, [0, 0, 0])
    title = _path_get(item, [0, 3])
    if not isinstance(app_id, str) or not isinstance(title, str):
        return None
    price_micros = _path_get(item, [0, 8, 1, 0, 0])
    currency = _path_get(item, [0, 8, 1, 0, 1])
    if isinstance(price_micros, (int, float)):
        price_amount = round(price_micros / 1_000_000, 2)
    else:
        price_amount = 0.0
    return {
        "app_id": app_id,
        "name": title,
        "developer": _path_get(item, [0, 14]),
        "icon_url": _path_get(item, [0, 1, 3, 2]),
        "price_amount": price_amount,
        "currency": currency if isinstance(currency, str) else None,
        "rating": _path_get(item, [0, 4, 1]),
        "rating_count": None,
    }


def parse_app_item(item, rank: int) -> dict:
    parsed = _parse_variant_a(item) or _parse_variant_b(item)
    if parsed is None:
        raise FetchError("unsupported Google Play app entry structure")
    parsed["rank"] = rank
    if not parsed.get("name"):
        parsed["name"] = f"App {parsed['app_id']}"
    return parsed


def select_play_categories() -> list[dict]:
    selected = [{"id": "all", "name": "总榜"}]
    selected.extend(
        {"id": category_id, "name": config.play_category_display_name(category_id)}
        for category_id in config.PLAY_APP_CATEGORY_IDS
    )
    selected.append({"id": "GAME", "name": "游戏"})
    selected.extend(
        {"id": category_id, "name": config.play_category_display_name(category_id)}
        for category_id in config.PLAY_GAME_SUBCATEGORY_IDS
    )
    return selected


def chart_url(country: str, chart_type: str, category_id: str) -> str:
    collection = config.PLAY_COLLECTIONS[chart_type]
    if category_id and category_id != "all":
        base = f"{PLAY_URL}/category/{category_id}/collection/{collection}"
    else:
        base = f"{PLAY_URL}/collection/{collection}"
    return f"{base}?hl=en&gl={country}"


def fetch_chart(
    country: str,
    chart_type: str,
    category: dict,
    top_n: int = config.TOP_N,
) -> list[dict]:
    try:
        app_list = _ensure_country_session(country)
    except FetchError:
        app_list = []
    if not app_list:
        app_list = _batch_fetch(country, chart_type, category["id"], top_n)
    if not app_list:
        raise FetchError(
            f"no app list found for {country}/{chart_type}/{category['id']}"
        )
    return [
        parse_app_item(item, index + 1)
        for index, item in enumerate(app_list[:top_n])
    ]


def _fetch_one(country: str, chart_type: str, category: dict, top_n: int) -> dict:
    entries = fetch_chart(country, chart_type, category, top_n=top_n)
    return {
        "country": country,
        "chart_type": chart_type,
        "category": category,
        "entries": entries,
    }


def fetch_day(
    date: str,
    db_path: Path = config.DB_PATH,
    regions: list[str] | None = None,
    charts: list[str] | None = None,
    top_n: int = config.TOP_N,
) -> dict:
    """Fetch daily Google Play snapshots for configured regions/charts."""
    db.init_db(db_path)
    region_keys = regions or list(config.REGIONS.keys())
    chart_keys = charts or list(config.CHART_TYPES.keys())
    countries = [c for c in config.iter_countries() if c.region in region_keys]
    conn = db.connect(db_path)
    try:
        db.clear_play_snapshots(conn, date, [c.code for c in countries], chart_keys)
    finally:
        conn.close()

    stats = {
        "date": date,
        "regions": region_keys,
        "charts": chart_keys,
        "countries": len(countries),
        "feeds_total": 0,
        "feeds_ok": 0,
        "feeds_failed": [],
        "entries_total": 0,
        "saved_snapshots": 0,
    }
    fetched_at = datetime.now().astimezone().isoformat(timespec="seconds")
    categories = select_play_categories()

    for country in countries:
        tasks = [
            (country.code, chart_type, category, top_n)
            for chart_type in chart_keys
            for category in categories
        ]
        stats["feeds_total"] += len(tasks)
        snapshots: list[tuple[str, str, str, str, list[dict]]] = []
        with ThreadPoolExecutor(max_workers=config.PLAY_WORKERS) as executor:
            futures = [executor.submit(_fetch_one, *task) for task in tasks]
            for future in as_completed(futures):
                try:
                    result = future.result()
                    snapshots.append(
                        (
                            result["country"],
                            result["chart_type"],
                            result["category"]["id"],
                            result["category"]["name"],
                            result["entries"],
                        )
                    )
                    stats["feeds_ok"] += 1
                    stats["entries_total"] += len(result["entries"])
                except Exception as exc:  # noqa: BLE001 - keep going per feed
                    LOGGER.warning("google play feed failed: %s", exc)
                    stats["feeds_failed"].append(str(exc))

        conn = db.connect(db_path)
        try:
            with conn:
                for country_code, chart_type, category_id, category_name, entries in snapshots:
                    db.replace_play_snapshot(
                        conn,
                        date,
                        country.region,
                        country_code,
                        chart_type,
                        category_id,
                        category_name,
                        entries,
                        fetched_at,
                    )
                    stats["saved_snapshots"] += 1
        finally:
            conn.close()

    return stats
