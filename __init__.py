# Copyright 2017 Mycroft AI, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import re
import sys
import wikipedia as wiki

from mycroft.skills.common_query_skill import CommonQuerySkill, CQSMatchLevel
from concurrent.futures import ThreadPoolExecutor
from mycroft.skills.skill_data import read_vocab_file
from adapt.intent import IntentBuilder
from mycroft import intent_handler

EXCLUDED_IMAGES = [
    'https://upload.wikimedia.org/wikipedia/commons/7/73/Blue_pencil.svg'
]

def wiki_image(pagetext):
    """Fetch first best image from results.

    Arguments:
        pagetext: wikipedia result page

    Returns:
        (str) image url or empty string if no image available
    """
    images = [i for i in pagetext.images if i not in EXCLUDED_IMAGES]
    if len(images) > 0:
        return images[0]
    else:
        return ''

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
        wiki.set_lang(lang_code)

        # Fetch wiki article titles. This comes back
        # as a list. "beans" returns ['beans', 'Green beans']
        results = wiki.search(search, 5)

        if len(results) == 0:
            return None

        return PageMatch(results[0], auto_suggest)

    except wiki.exceptions.DisambiguationError as e:
        # Test: "tell me about john"
        return PageDisambiguation(e.options)

class PageDisambiguation:
    """Class representing a disambiguation request."""
    def __init__(self, options):
        self.options = options[:5]

class PageMatch:
    """Representation of a wiki page match.

    This class contains the necessary data for the skills responses.
    """
    def __init__(self, result=None, auto_suggest=None,
                 summary=None, lines=None, image=None):

        if not (summary and lines):
            summary, lines = self._wiki_page_summary(result, auto_suggest)

        self.summary = summary
        self.lines = lines

        self.image = image or wiki_image(
            wiki.page(result, auto_suggest=auto_suggest)
        )
        self.auto_suggest = auto_suggest
        self.wiki_result = result

    def _wiki_page_summary(self, result, auto_suggest):
        """Request the summary for the result.

        writes in inverted-pyramid style, so the first sentence is the
        most important, the second less important, etc.  Two sentences
        is all we ever need.

        Arguments:
            wiki result (str): Wikipedia match name
            auto_suggest (bool): True if auto suggest was used to get this
                                 result.
        """
        lines = 20
        summary = wiki.summary(result, lines, auto_suggest=auto_suggest)

        if "==" in summary or len(summary) > 2500:
            # We hit the end of the article summary or hit a really 
            # long one.  Reduce to first line.
            # TODO - this could be better, correct this eventually
            lines = 1
            summary = wiki.summary(result, lines, auto_suggest=auto_suggest)

        # Clean text to make it more speakable
        return re.sub(r'\([^)]*\)|/[^/]*/', '', summary), lines

class WikipediaSkill(CommonQuerySkill):
    """TODO these should also be moved out to a voc file
    so we have a chance at supporting something
    besides english.

    Only ones that make sense in
    <question_word> <question_verb> <noun>"""
    question_words = ['who', 'whom', 'what', 'when']
    # Note the spaces
    question_verbs = [' is', '\'s', 's', ' are', '\'re',
                      're', ' did', ' was', ' were']
    articles = ['a', 'an', 'the', 'any']

    def __init__(self):
        super(WikipediaSkill, self).__init__()
        fname = self.find_resource("Wikipedia.voc", res_dirname="vocab")
        temp = read_vocab_file(fname)
        vocab = []
        for item in temp:
            vocab.append( " ".join(item) )
        self.sorted_vocab = sorted(vocab, key=lambda x: (-len(x), x))

    def get_wiki_result(self, search):
        """Search wiki and Handle disambiguation.

        This runs the auto_suggest and non-auto-suggest versions in parallell
        to improve speed.

        Arguments:
            search (str): String to seach for

        Returns:
            PageMatch, PageDisambiguation or None
        """
        lang_code = self.translate_namedvalues("wikipedia_lang")['code']

        def lookup(auto_suggest):
            try:
                return wiki_lookup(search, lang_code, auto_suggest)
            except wiki.PageError:
                self.log.debug("Wiki page error")
                return None
            except Exception as e:
                self.log.error("Error: {0}".format(e))
                return None

        with ThreadPoolExecutor() as pool:
            res_auto_suggest, res_without_auto_suggest = (
                list(pool.map(lookup, (True, False)))
            )
        ret = res_without_auto_suggest
        return ret

    def respond(self, query):
        result = self.get_wiki_result(query)
        if result is not None:
            if isinstance(result, PageMatch):
                result = result.summary
            elif isinstance(result, PageDisambiguation):
                # we auto disambiguate here 
                if len(result.options) > 0:
                    result = self.get_wiki_result(result.options[0])
                    if result is not None:
                        result = result.summary
                else:
                    result = None

        return result

    def fix_input(self, query):
        for noun in self.question_words:
            for verb in self.question_verbs:
                for article in [i + ' ' for i in self.articles] + ['']:
                    test = noun + verb + ' ' + article
                    if query[:len(test)] == test:
                        return query[len(test):]
        return query

    def CQS_match_query_phrase(self, query):
        answer = None
        test = self.fix_input(query)

        if test is not None:
            answer = self.respond(test)

        if answer:
            return (query, CQSMatchLevel.CATEGORY, answer)
        return answer

    def stop(self):
        pass

    @intent_handler(IntentBuilder("AskWiki").require("Wikipedia"))
    def handle_ask_wiki(self, message):
        """entry point when wiki is called out by name
           in the utterance"""
        utt = message.data['utterance']

        if utt is None:
            return

        # consider this pre processing for fix_input()
        # it removes the intent specific predicates
        for voc in self.sorted_vocab:
            utt = utt.replace(voc,"")
        utt = utt.strip()

        utt = self.fix_input(utt)

        if utt is not None:
            response = self.respond(utt)
            self.speak("Here is your answer from wiki peedia")
            self.speak(response)

def create_skill():
    return WikipediaSkill()
