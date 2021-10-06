# Copyright 2017, Mycroft AI Inc.
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
from concurrent.futures import ThreadPoolExecutor

import wikipedia as wiki
from mycroft.audio import wait_while_speaking
from mycroft.skills import AdaptIntent, intent_handler
from mycroft.skills.common_query_skill import CommonQuerySkill, CQSMatchLevel
from mycroft.skills.skill_data import read_vocab_file
from mycroft.util.format import join_list
from mycroft.util.log import LOG
from quebra_frases import sentence_tokenize

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

        self.page = wiki.page(result, auto_suggest=auto_suggest)
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
            summary = wiki.summary(
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

    def get_image(self):
        """Fetch image for this wiki page."""
        self.image = self._find_best_image()
        return self.image


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
        # as a list.  I.e. "beans" returns ['beans',
        #     'Beans, Beans the Music Fruit', 'Phaseolus vulgaris',
        #     'Baked beans', 'Navy beans']
        results = wiki.search(search, 5)
        if len(results) == 0:
            return None

        return PageMatch(results[0], auto_suggest)

    except wiki.exceptions.DisambiguationError as e:
        # Test: "tell me about john"
        return PageDisambiguation(e.options)


class WikipediaSkill(CommonQuerySkill):
    def __init__(self):
        """ self.auto_more (bool): From config "cq_auto_more": if true will
           return abbreviated (2 lines) and handle 
           'more'. If false (or not present), will
           return entire abstract and handle 'stop'"""
        super(WikipediaSkill, self).__init__(name="WikipediaSkill")
        self._match = None
        self._lines_spoken_already = 0

        fname = self.find_resource("Wikipedia.voc", res_dirname="vocab")
        temp = read_vocab_file(fname)
        vocab = []
        for item in temp:
            vocab.append(" ".join(item))
        self.sorted_vocab = sorted(vocab, key=lambda x: (-len(x), x))

        self.translated_question_words = self.translate_list("question_words")
        self.translated_question_verbs = self.translate_list("question_verbs")
        self.translated_articles = self.translate_list("articles")

        self.auto_more = self.config_core.get('cq_auto_more', False)

    @intent_handler(AdaptIntent("").require("Wikipedia").
                    require("ArticleTitle"))
    def handle_wiki_query(self, message):
        """Extract what the user asked about and reply with info from wikipedia.
        """
        search = message.data.get("ArticleTitle")
        # Talk to the user, as this can take a little time...
        self.speak_dialog("searching", {"query": search})
        self.handle_result(self.get_wiki_result(search))

    def handle_result(self, result):
        """Handle result depending on result type.

        Speaks appropriate feedback to user depending of the result type.
        Arguments:
            result (object): wiki result object to handle.
        """
        if result is None:
            self.respond_no_match()
        elif isinstance(result, PageMatch):
            self.respond_match(result)
        elif isinstance(result, PageDisambiguation):
            self.respond_disambiguation(result)

    def respond_no_match(self):
        """Answer no match found."""
        self.speak_dialog("no entry found")

    def respond_match(self, match):
        """Read short summary to user."""
        match.get_image()
        self.display_article(match)
        # Remember context and speak results
        self._match = match
        self.set_context("wiki_article", "")
        if self.auto_more:
            self._lines_spoken_already = 20
            self.speak(match[:20])
        else:
            self._lines_spoken_already = match.intro_length
            self.speak(match.get_intro())

    def respond_disambiguation(self, disambiguation):
        """Ask for which of the different matches should be used."""
        options = join_list(disambiguation.options, 'or', lang=self.lang)
        choice = self.get_response('disambiguate', data={"options": options})

        self.log.info('Disambiguation choice is {}'.format(choice))
        if choice:
            self.handle_result(self.get_wiki_result(choice))

    @intent_handler(AdaptIntent("").require("More").require("wiki_article"))
    def handle_tell_more(self, message):
        """Follow up query handler, "tell me more".

        If a "spoken_lines" entry exists in the active contexts
        this can be triggered.
        """
        # Read more of the last article queried
        if not self._match:
            self.log.error('handle_tell_more called without previous match')
            return

        article = self._match
        start = self._lines_spoken_already
        stop = self._lines_spoken_already + 5
        summary = article[start:stop]

        if summary:
            self.display_article(article)
            self.speak(summary)
            # Update context
            self._lines_spoken_already += 5
            self.set_context("wiki_article", "")
        else:
            self.speak_dialog("thats all")

    @intent_handler("Random.intent")
    def handle_random_intent(self, _):
        """ Get a random wiki page.

        Uses the Special:Random page of wikipedia
        """
        # Talk to the user, as this can take a little time...
        lang_code = self.translate_namedvalues("wikipedia_lang")['code']
        search = wiki.random(pages=1)
        self.speak_dialog("searching", {"query": search})
        result = wiki_lookup(search, lang_code)
        self.handle_result(result)

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
                return None
            except Exception as e:
                self.log.error("Error: {0}".format(e))
                return None

        with ThreadPoolExecutor() as pool:
            """rather than gut it I simply disable 
            it for now but once fixed change this to 
            (True, False). This fixes the Jira bug
            wiki returns cat for what is an automobile"""
            res_auto_suggest, res_without_auto_suggest = (
                list(pool.map(lookup, (False, False)))
            )
        # Check the results, return PageMatch (autosuggest
        # preferred) otherwise return the autosuggest
        # PageDisambiguation.
        if ((isinstance(res_auto_suggest, PageDisambiguation) or
             (res_auto_suggest is None)) and
                isinstance(res_without_auto_suggest, PageMatch)):
            ret = res_without_auto_suggest
        else:
            ret = res_auto_suggest
        return ret

    def display_article(self, match):
        """Display the match page on a GUI if connected.

        Arguments:
            match (PageMatch): wiki page match
        """
        self.gui.clear()
        self.gui['title'] = match.wiki_result
        self.gui['summary'] = match.summary
        self.gui['imgLink'] = match.image
        self.gui.show_image(match.image, title=match.wiki_result)
        # self.gui.show_page("WikipediaDelegate.qml", override_idle=60)

    def respond(self, query):
        """determine if we have a page match or 
        disambiguate response. if a disambiguate 
        match perform auto-disambiguation"""
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
        # Trim response to correct length
        if result is not None:
            if self.auto_more:
                result = result[:20]
            else:
                result = result[:2]
        return ' '.join(result)

    def fix_input(self, query):
        for noun in self.translated_question_words:
            for verb in self.translated_question_verbs:
                for article in [i + ' ' for i in self.translated_articles] + ['']:
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
        self.gui.release()


def create_skill():
    return WikipediaSkill()
