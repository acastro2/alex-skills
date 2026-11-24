import re


def slugify(title):
    return "-".join(re.findall(r"[a-z0-9]+", title.lower()))
