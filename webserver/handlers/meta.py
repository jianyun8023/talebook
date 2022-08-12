#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
import logging
import math
import sys
from functools import cmp_to_key
from gettext import gettext as _

import meilisearch

from webserver import utils
from webserver.handlers.base import ListHandler, js


class AuthorBooksUpdate(ListHandler):
    def post(self, name):
        category = "authors"
        author_id = self.cache.get_item_id(category, name)
        ids = self.db.get_books_for_category(category, author_id)
        for book_id in list(ids)[:40]:
            self.do_book_update(book_id)
        self.redirect("/author/%s" % name, 302)


class PubBooksUpdate(ListHandler):
    def post(self, name):
        category = "publisher"
        publisher_id = self.cache.get_item_id(category, name)
        if publisher_id:
            ids = self.db.get_books_for_category(category, publisher_id)
        else:
            ids = self.cache.search_for_books("")
            books = self.db.get_data_as_dict(ids=ids)
            ids = [b["id"] for b in books if not b["publisher"]]
        for book_id in list(ids)[:40]:
            self.do_book_update(book_id)
        self.redirect("/publisher/%s" % name, 302)


class MetaList(ListHandler):
    @js
    def get(self, meta):
        SHOW_NUMBER = 300
        if self.get_argument("show", "") == "all":
            SHOW_NUMBER = sys.maxsize
        titles = {
            "tag": _(u"全部标签"),
            "author": _(u"全部作者"),
            "series": _(u"丛书列表"),
            "rating": _(u"全部评分"),
            "publisher": _(u"全部出版社"),
        }
        title = titles.get(meta, _(u"未知")) % vars()
        # category = meta if meta in ["series", "publisher"] else meta + "s"
        items = self.get_category_with_count(meta)
        count = len(items)
        if items:
            if meta == "rating":
                items.sort(key=lambda x: x["name"], reverse=True)
            else:
                hotline = int(math.log10(count)) if count > SHOW_NUMBER else 0
                items = [v for v in items if v["count"] >= hotline]
                items.sort(key=lambda x: x["count"], reverse=True)
        return {"meta": meta, "title": title, "items": items, "total": count}


class MetaBooks(ListHandler):
    @js
    def get(self, meta, name):
        titles = {
            "tag": _(u'含有"%(name)s"标签的书籍'),
            "author": _(u'"%(name)s"编著的书籍'),
            "series": _('"%(name)s"丛书包含的书籍'),
            "rating": _("评分为%(name)s星的书籍"),
            "publisher": _(u'"%(name)s"出版的书籍'),
        }
        title = titles.get(meta, _(u"未知")) % vars()  # noqa: F841
        category = meta + "s" if meta in ["tag", "author"] else meta
        if meta in ["rating"]:
            name = int(name)
        client = meilisearch.Client('http://192.168.2.4:7700')
        start, size = self.get_page_param()
        if meta == "tag":

            document = client.index("books").search("", {
                "limit": size,
                "offset": start,
                "sort": ["id:desc"],
                "filter": "tags = " + name
            })

            count = document["estimatedTotalHits"]
            books = document['hits']
            return {
                "err": "ok",
                "title": title,
                "total": count,
                "books": [self.fmt(b) for b in books],
            }
        elif meta == "author":
            document = client.index("books").search("", {
                "limit": size,
                "offset": start,
                "sort": ["id:desc"],
                "filter": "authors = " + name
            })

            count = document["estimatedTotalHits"]
            books = document['hits']
            return {
                "err": "ok",
                "title": title,
                "total": count,
                "books": [self.fmt(b) for b in books],
            }
        elif meta == "publisher":
            document = client.index("books").search("", {
                "limit": size,
                "offset": start,
                "sort": ["id:desc"],
                "filter": "publisher = " + name
            })

            count = document["estimatedTotalHits"]
            books = document['hits']
            return {
                "err": "ok",
                "title": title,
                "total": count,
                "books": [self.fmt(b) for b in books],
            }

        books = self.get_item_books(category, name)
        books.sort(key=cmp_to_key(utils.compare_books_by_rating_or_id), reverse=True)
        return self.render_book_list(books, title=title)


def routes():
    return [
        (r"/api/(author|publisher|tag|rating|series)", MetaList),
        (r"/api/(author|publisher|tag|rating|series)/(.*)", MetaBooks),
        (r"/api/author/(.*)/update", AuthorBooksUpdate),
        (r"/api/publisher/(.*)/update", PubBooksUpdate),
    ]
