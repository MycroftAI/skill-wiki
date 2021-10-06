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

from concurrent.futures import ThreadPoolExecutor

from mycroft.skills import AdaptIntent, intent_handler
from mycroft.skills.common_query_skill import CommonQuerySkill, CQSMatchLevel
from mycroft.util.format import join_list

from .wiki.pages import PageMatch, PageDisambiguation, PageError
from .wiki.search import get_random_wiki_page, wiki_lookup

EXCLUDED_IMAGES = [
    'https://upload.wikimedia.org/wikipedia/commons/7/73/Blue_pencil.svg'
]


class WikipediaSkill(CommonQuerySkill):
    def __init__(self):
        """Constructor for WikipediaSkill.

        Attributes:
            _match (PageMatch): current match in case user requests more info
            _lines_spoken_already (int): number of lines already spoken from _match.summary
            translated_question_words (list[str]): used in cleaning queries
            translated_question_verbs (list[str]): used in cleaning queries
            translated_articles (list[str]): used in cleaning queries
        """
        super(WikipediaSkill, self).__init__(name="WikipediaSkill")
        self._match = None
        self._lines_spoken_already = 0
        self.translated_question_words = self.translate_list("question_words")
        self.translated_question_verbs = self.translate_list("question_verbs")
        self.translated_articles = self.translate_list("articles")

    @intent_handler(AdaptIntent().require("Wikipedia").
                    require("ArticleTitle"))
    def handle_wiki_query(self, message):
        """Extract what the user asked about and reply with info from wikipedia.
        """
        search = message.data.get("ArticleTitle")
        # Talk to the user, as this can take a little time...
        self.speak_dialog("searching", {"query": search})
        self.handle_result(self.get_wiki_result(search))

    @intent_handler("Random.intent")
    def handle_random_intent(self, _):
        """ Get a random wiki page.

        Uses the Special:Random page of wikipedia
        """
        # Talk to the user, as this can take a little time...
        lang_code = self.translate_namedvalues("wikipedia_lang")['code']
        search = get_random_wiki_page()
        self.speak_dialog("searching", {"query": search})
        result = wiki_lookup(search, lang_code)
        self.handle_result(result)

    @intent_handler(AdaptIntent().require("More").require("wiki_article"))
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

    def CQS_match_query_phrase(self, query: str) -> tuple([str, CQSMatchLevel, str, dict]):
        """Respond to Common Query framework with best possible answer.

        Args:
            query: question to answer

        Returns:
            Tuple(
                question being answered,
                CQS Match Level confidence,
                answer to question,
                callback dict available to CQS_action method
            )
        """
        answer = None
        callback_data = dict()
        cleaned_query = self.extract_topic(query)

        if cleaned_query is not None:
            answer, result = self._get_best_guess_answer(cleaned_query)

        if result:
            callback_data = {
                'title': result.wiki_result,
                'summary': result.summary,
                'image': result.image
            }
        if answer:
            return (query, CQSMatchLevel.CATEGORY, answer, callback_data)
        return answer

    def CQS_action(self, phrase: str, data: dict):
        """Display result if selected by Common Query to answer.

        Note common query will speak the response.

        Args:
            phrase: User utterance of original question
            data: Callback data specified in CQS_match_query_phrase()
        """
        self._display_article_from_dict(data)

    def extract_topic(self, query: str) -> str:
        """Extract the topic of a query.

        Args:
            query: user utterance eg 'what is the earth'
        Returns:
            topic of question eg 'earth' or original query
        """
        for noun in self.translated_question_words:
            for verb in self.translated_question_verbs:
                for article in [i + ' ' for i in self.translated_articles] + ['']:
                    test = noun + verb + ' ' + article
                    if query[:len(test)] == test:
                        return query[len(test):]
        return query

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
            except PageError:
                return None
            except Exception as e:
                self.log.error("Error: {0}".format(e))
                return None

        with ThreadPoolExecutor() as pool:
            res_auto_suggest, res_without_auto_suggest = (
                list(pool.map(lookup, (True, False)))
            )
        # Check the results, return PageMatch (without auto_suggest preferred)
        # otherwise return the auto_suggest that may be a PageMatch or
        # PageDisambiguation.
        # Previously preferenced with auto_suggest however it is returning
        # incorrect results eg "tell me about automobiles" returns cats.
        if isinstance(res_without_auto_suggest, PageMatch):
            ret = res_without_auto_suggest
        else:
            ret = res_auto_suggest
        return ret

    def _get_best_guess_answer(self, query: str) -> str:
        """Get the best guess answer for a given query.

        First determine if we have a page match or disambiguate response.
        If a disambiguate match perform auto-disambiguation.

        Args:
            query: question from user
        Returns
            answer to question, page result
        """
        answer = ''
        result = self.get_wiki_result(query)
        if isinstance(result, PageDisambiguation):
            # we auto disambiguate here
            if len(result.options) > 0:
                result = self.get_wiki_result(result.options[0])
            else:
                result = None
        if result is not None:
            answer, _ = self.get_answer_from_result(result)
        return answer, result

    def get_answer_from_result(self, result: PageMatch) -> tuple([str, int]):
        """Get an answer of the correct length from the start of the summary.

        About auto_more (bool): default False
            Set by cq_auto_more attribute in mycroft.conf
            If true will read 20 lines of abstract for any query.
            If false will read first 2 lines and wait for request to read more.

        Args:
            result: PageMatch of successful query
        Returns:
            trimmed answer, number of sentences
        """
        auto_more = self.config_core.get('cq_auto_more', False)

        if auto_more:
            length = 20
            answer = ' '.join(result.summary[:length])
        else:
            length = result.intro_length
            answer = result.get_intro()
        return answer, length

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
        answer, answer_length = self.get_answer_from_result(match)
        self._lines_spoken_already = answer_length
        self.speak(answer)

    def respond_disambiguation(self, disambiguation):
        """Ask for which of the different matches should be used."""
        options = join_list(disambiguation.options, 'or', lang=self.lang)
        choice = self.get_response('disambiguate', data={"options": options})

        self.log.info('Disambiguation choice is {}'.format(choice))
        if choice:
            self.handle_result(self.get_wiki_result(choice))

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

    def _display_article_from_dict(self, data: dict):
        """Display the page data on a GUI if connected.

        Used by CQS as the data is serialized.

        Arguments:
            data: wiki page data {
                title: page title
                summary: summary of page contents
                image: url of image to display
            }
        """
        if not self.gui.connected:
            return
        self.gui.clear()
        self.gui['title'] = data.get('title', 'From Wikipedia')
        self.gui['summary'] = data.get('summary', '')
        self.gui['imgLink'] = data.get('image', '')
        self.gui.show_image(data.get('image', ''),
                            title=data.get('title', 'From Wikipedia'))
        # self.gui.show_page("WikipediaDelegate.qml", override_idle=60)

    def stop(self):
        self.gui.release()


def create_skill():
    return WikipediaSkill()
