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
from mycroft import intent_handler
from mycroft.skills import AdaptIntent
from mycroft.skills.common_query_skill import CommonQuerySkill, CQSMatchLevel
from mycroft.skills.skill_data import read_vocab_file
from mycroft.util.format import join_list
from mycroft.util.log import LOG

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


class PageDisambiguation:
    """Class representing a disambiguation request."""

    def __init__(self, options):
        self.options = options[:5]


class PageMatch:
    """Representation of a wiki page match.

    This class contains the necessary data for the skills responses.
    """

    def __init__(self, result=None, auto_suggest=None,
                 summary=None, lines=None, image=None,
                 auto_more=False):

        self.auto_more = auto_more

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
        if self.auto_more:
            lines = 2
            summary = wiki.summary(result, lines, auto_suggest=auto_suggest)

            if "==" in summary or len(summary) > 250:
                # We hit the end of the article summary or hit a really long
                # one.  Reduce to first line.
                lines = 1
                summary = wiki.summary(
                    result, lines, auto_suggest=auto_suggest)
        else:
            lines = 20
            summary = wiki.summary(result, lines, auto_suggest=auto_suggest)

            if "==" in summary or len(summary) > 2500:
                lines = 2
                summary = wiki.summary(
                    result, lines, auto_suggest=auto_suggest)

        # Clean text to make it more speakable
        return re.sub(r'\([^)]*\)|/[^/]*/', '', summary), lines


def wiki_lookup(search, lang_code, auto_suggest=True, auto_more=False):
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

        return PageMatch(results[0], auto_suggest, auto_more=auto_more)

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

        self.display_article(match)
        # Remember context and speak results
        self._match = match
        self.set_context("wiki_article", "")
        self._lines_spoken_already = match.lines
        self.speak(match.summary)

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
        summary_read = wiki.summary(article.wiki_result,
                                    self._lines_spoken_already,
                                    auto_suggest=article.auto_suggest)
        summary = wiki.summary(article.wiki_result,
                               self._lines_spoken_already + 5,
                               auto_suggest=article.auto_suggest)
        self._lines_spoken_already += 5

        # Remove already-spoken parts and section titles
        summary = summary[len(summary_read):]
        summary = re.sub(r'\([^)]*\)|/[^/]*/|== [^=]+ ==', '', summary)

        if not summary:
            self.speak_dialog("thats all")
        else:
            self.display_article(article)
            self.speak(summary)
            # Update context
            self.set_context("wiki_article", "")

    @intent_handler("Random.intent")
    def handle_random_intent(self, _):
        """ Get a random wiki page.

        Uses the Special:Random page of wikipedia
        """
        # Talk to the user, as this can take a little time...
        lang_code = self.translate_namedvalues("wikipedia_lang")['code']
        search = wiki.random(pages=1)
        self.speak_dialog("searching", {"query": search})
        self.handle_result(wiki_lookup(
            search, lang_code, auto_more=self.auto_more))

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
                return wiki_lookup(search, lang_code, auto_suggest, auto_more=self.auto_more)
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
        self.gui['summary'] = match.summary
        self.gui['imgLink'] = match.image
        self.gui.show_page("WikipediaDelegate.qml", override_idle=60)

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

        return result

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
