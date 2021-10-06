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

import wikipedia

from .pages import PageDisambiguation, PageMatch


def get_random_wiki_page():
    """Get a random wikipedia page."""
    return wikipedia.random(pages=1)

def wiki_lookup(search, lang_code, auto_suggest=True):
    """Performs a wikipedia article lookup.

    Arguments:
        search (str): phrase to search for
        lang_code (str): wikipedia language code to use
        auto_suggest (bool): wether or not to use autosuggest.

    Returns:
        PageMatch, PageDisambiguation or None
    """
    try:
        # Use the version of Wikipedia appropriate to the request language
        wikipedia.set_lang(lang_code)

        # Fetch wiki article titles. This comes back
        # as a list.  I.e. "beans" returns ['beans',
        #     'Beans, Beans the Music Fruit', 'Phaseolus vulgaris',
        #     'Baked beans', 'Navy beans']
        results = wikipedia.search(search, 5)
        if len(results) == 0:
            return None

        return PageMatch(results[0], auto_suggest)

    except wikipedia.exceptions.DisambiguationError as e:
        # Test: "tell me about john"
        return PageDisambiguation(e.options)