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

import re

from quebra_frases import sentence_tokenize

import wikipedia
from wikipedia import PageError

EXCLUDED_IMAGES = [
    'https://upload.wikimedia.org/wikipedia/commons/7/73/Blue_pencil.svg'
]


class PageDisambiguation:
    """Class representing a disambiguation request."""

    def __init__(self, options):
        self.options = options[:5]


class PageMatch:
    """Representation of a wiki page match.

    This class contains the necessary data for the skills responses.
    """

    def __init__(self, result=None, auto_suggest=None):

        self.wiki_result = result
        self.auto_suggest = auto_suggest

        self.page = wikipedia.page(result, auto_suggest=auto_suggest)
        self.summary = self._get_page_summary()
        self.intro_length = self._get_intro_length()

    def _get_page_summary(self) -> list([str]):
        """Get the summary from the wiki page.

        Writes in inverted-pyramid style, so the first sentence is the
        most important, the second less important, etc. Two sentences
        is all we ever need.

        Returns
            List: summary as list of sentences
        """
        if hasattr(self.page, 'summary'):
            summary = self.page.summary
        else:
            summary = wikipedia.summary(
                self.wiki_result, auto_suggest=self.auto_suggest)

        # Clean text to make it more speakable
        summary = re.sub(r'\([^)]*\)|/[^/]*/', '', summary)
        summary = re.sub(r'\s+', ' ', summary)
        return sentence_tokenize(summary)

    def _get_intro_length(self):
        default_intro = '. '.join(self.summary[:2])
        if len(default_intro) > 250 or '==' in default_intro:
            return 1
        else:
            return 2

    def get_intro(self):
        """Get the intro sentences for the match."""
        return self[:self.intro_length]

    def __getitem__(self, val):
        """Implements slicing for the class, returning a chunk of text.

        Can either return a single sentence from the article or a range
        of sentences. The sentences are prepared and formated into a single
        string.
        """
        lines = self.summary.__getitem__(val)
        if lines:
            return ' '.join(lines)
        else:
            return ''

    def _find_best_image(self):
        """Find the best image for this wiki page.

        Preference given to the official thumbnail.

        Returns:
            (str) image url or empty string if no image available
        """
        image = ''
        if hasattr(self.page, 'thumbnail'):
            image = self.page.thumbnail
        else:
            images = [i for i in self.page.images if i not in EXCLUDED_IMAGES]
            if len(images) > 0:
                image = images[0]
        return image

    @property
    def image(self):
        """Image for this wiki page."""
        return self._find_best_image()
