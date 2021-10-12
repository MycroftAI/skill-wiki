# Copyright 2021, Mycroft AI Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from urllib3.exceptions import HTTPError

from mediawiki import (
    MediaWiki,
    MediaWikiPage,
    PageError,
    DisambiguationError
)

from mycroft.util import LOG


DEFAULT_IMAGE = 'ui/default-images/wikipedia-logo.svg'
EXCLUDED_IMAGES = [
    'Blue_pencil.svg',
    'OOjs_UI_icon_edit-ltr-progressive.svg'
]


class Wiki():
    """Interface to Wikipedia using pymediawiki."""

    def __init__(self, lang) -> None:
        self.default_lang = lang
        try:
            self.wiki = MediaWiki(lang=lang)
        except HTTPError:
            raise

    def get_best_image_url(self, page: MediaWikiPage) -> str:
        """Get url of the best image from an existing Wiki page.

        Preference is given to the page thumbnail, otherwise we get the first
        image on the page that is not intentionally excluded.
        eg the pencil/edit icon

        Note: Calling `page.logos` is a parsing operation and not part of the
              standard API. It is not accessing existing data on the
              MediaWikiPage object and it is a slower operation.

        Args:
            page: target wikipedia page
        Returns:
            url of best image
        """
        image = None
        if len(page.logos) > 0:
            thumbnail = page.logos[0]
            # Get hi-res image if available.
            # This translates image urls between the following two formats
            # https://upload.wikimedia.org/wikipedia/commons/thumb/d/d4/Sialyl_lewis_a.svg/200px-Sialyl_lewis_a.svg.png
            # https://upload.wikimedia.org/wikipedia/commons/d/d4/Sialyl_lewis_a.svg
            full_image = '/'.join(thumbnail.replace('/thumb/',
                                  '/').split('/')[:-1])
            image = full_image if full_image in page.images else thumbnail
        elif len(page.images) > 0:
            image = next(img for img in page.images if img.split(
                '/')[-1] not in EXCLUDED_IMAGES)

        LOG.debug('Image selected: %s', image)
        LOG.debug('From page.logos:')
        for url in page.logos:
            LOG.debug(' - %s', url)
        LOG.debug('and page.images:')
        for url in page.images:
            LOG.debug(' - %s', url)

        return image or DEFAULT_IMAGE

    def get_page(self, title: str) -> MediaWikiPage:
        """Get the specified wiki page."""
        try:
            page = self.wiki.page(title)
        except PageError:
            page = None
        return page

    def get_random_page(self, lang: str = 'en') -> MediaWikiPage:
        """Get a random wikipedia page.

        Uses the Special:Random page of Wikipedia
        """
        self.set_language('en')
        random_page = self.wiki.random(pages=1)
        return self.get_page(random_page)

    def search(self, query: str, lang: str = 'en') -> list([str]):
        """Search wikipedia for the given query.

        Args:
            query: search term to use
            lang: language of the request

        Returns:
            list of results
        """
        self.set_language(lang)
        return self.wiki.search(query)

    def set_language(self, lang: str) -> bool:
        """Set the language for Wikipedia lookups.

        If the provided language cannot be found. The language used when
        instantiating the Wiki class will be used.

        Args:
            lang: BCP-47 language code to use
        Returns:
            True if language changed successfully else False
        """
        if lang == self.default_lang:
            is_changed = False
        elif lang not in self.wiki.supported_languages.keys():
            LOG.warning('Unable to set Wikipedia language to "%s"', lang)
            is_changed = False
        else:
            LOG.info('Setting Wikipedia language to "%s"', lang)
            self.wiki.language = lang
            is_changed = True
        return is_changed
