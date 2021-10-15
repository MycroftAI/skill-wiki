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

from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
from urllib3.exceptions import HTTPError

from mycroft import AdaptIntent, intent_handler
from mycroft.skills.common_query_skill import CommonQuerySkill, CQSMatchLevel

from .wiki import Wiki, DisambiguationError, MediaWikiPage


Article = namedtuple(
    'Article', ['title', 'page', 'summary', 'num_lines_spoken', 'image'])
# Set default values to None.
# Once Python3.7 is min version, we can switch to:
# Article = namedtuple('Article', fields, defaults=(None,) * len(fields))
Article.__new__.__defaults__ = (None,) * len(Article._fields)


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
        self._match = self._cqs_match = Article()
        self.platform = self.config_core['enclosure'].get(
            'platform', 'unknown'
        )
        self.translated_question_words = self.translate_list("question_words")
        self.translated_question_verbs = self.translate_list("question_verbs")
        self.translated_articles = self.translate_list("articles")
        self._num_wiki_connection_attempts = 0
        self.init_wikipedia()

    def init_wikipedia(self):
        """Initialize the Wikipedia connection.

        If unable to connect it will retry every 10 minutes for up to 1 hour
        """
        self._num_wiki_connection_attempts += 1
        try:
            wikipedia_lang_code = self.translate_namedvalues("wikipedia_lang")[
                'code']
            auto_more = self.config_core.get('cq_auto_more', False)
            self.wiki = Wiki(wikipedia_lang_code, auto_more)
        except HTTPError:
            if self._num_wiki_connection_attempts < 1:
                self.log.warning(
                    "Cannot connect to Wikipedia. Will try again in 10 minutes")
                in_ten_minutes = 10 * 60
                self.schedule_event(self.init_wikipedia, in_ten_minutes)
            else:
                self.log.exception("Cannot connect to Wikipedia.")
        else:
            # Reset connection attempts if successful
            self._num_wiki_connection_attempts = 0

    @intent_handler(AdaptIntent().require("Wikipedia").
                    require("ArticleTitle"))
    def handle_direct_wiki_query(self, message):
        """Primary intent handler for direct wikipedia queries.

        Requires utterance to directly ask for Wikipedia's answer.
        """
        query = self.extract_topic(message.data.get("ArticleTitle"))
        # Talk to the user, as this can take a little time...
        self.speak_dialog("searching", {"query": query})
        try:
            page, disambiguation_page = self.search_wikipedia(query)
            self.log.info(f"Best result from Wikipedia is: {page.title}")
            self.handle_result(page)
            # TODO determine intended disambiguation behaviour
            # disabling disambiguation for now.
            if False and disambiguation_page is not None:
                self.log.info(
                    f"Disambiguation page available: {disambiguation_page}")
                if self.translate('disambiguate-exists') != 'disambiguate-exists':
                    # Dialog file exists and can be spoken
                    correct_topic = self.ask_yesno('disambiguate-exists')
                    if correct_topic != 'no':
                        return
                new_page = self.handle_disambiguation(disambiguation_page)
                if new_page is not None:
                    self.handle_result(new_page)
        except HTTPError:
            self.speak_dialog('connection-error')

    @intent_handler("Random.intent")
    def handle_random_intent(self, _):
        """ Get a random wiki page.

        Uses the Special:Random page of wikipedia
        """
        self.log.info("Fetching random Wikipedia page")
        lang = self.translate_namedvalues("wikipedia_lang")['code']
        page = self.wiki.get_random_page(lang=lang)
        self.log.info("Random page selected: %s", page.title)
        self.handle_result(page)

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

        summary_to_read, new_lines_spoken = self.wiki.get_summary_next_lines(
            self._match.page, self._match.num_lines_spoken)

        if summary_to_read:
            # TODO consider showing next image on page instead of same image each time.
            image = self.wiki.get_best_image_url(self._match.page)
            article = self._match._replace(
                summary=summary_to_read,
                num_lines_spoken=new_lines_spoken,
                image=image)
            self.display_article(article)
            self.speak(summary_to_read)
            # Update context
            self._match = article
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
            try:
                page, _ = self.search_wikipedia(cleaned_query)
            except HTTPError:
                return

        if page:
            callback_data = {'title': page.title}
            answer, num_lines = self.wiki.get_summary_intro(page)
            self._cqs_match = Article(page.title, page, answer, num_lines)
        if answer:
            self.schedule_event(self.get_cqs_match_image, 0)
            return (query, CQSMatchLevel.CATEGORY, answer, callback_data)
        return answer

    def CQS_action(self, phrase: str, data: dict):
        """Display result if selected by Common Query to answer.

        Note common query will speak the response.

        Args:
            phrase: User utterance of original question
            data: Callback data specified in CQS_match_query_phrase()
        """
        title = data.get('title')
        if title is None:
            self.log.error("No title returned from CQS match")
            return
        if self._cqs_match.title == title:
            title, page, summary, num_lines, image = self._cqs_match
        else:
            # This should never get called, but just in case.
            self.log.warning("CQS match data was not saved. "
                             "Please report this to Mycroft.")
            page = self.wiki.get_page(title)
            summary, num_lines = self.wiki.get_summary_intro(page)

        if image is None:
            image = self.wiki.get_best_image_url(page)
        article = Article(title, page, summary, num_lines, image)
        self.display_article(article)
        # Set context for follow up queries - "tell me more"
        self._match = article
        self.set_context("wiki_article", "")

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

    def search_wikipedia(self, query: str) -> tuple([MediaWikiPage, str]):
        """Handle Wikipedia query on topic.

        Args:
            query: search term to use
        Returns:
            wiki page for best result,
            disambiguation page title or None
        """
        self.log.info(f"Searching wikipedia for {query}")
        lang = self.translate_namedvalues("wikipedia_lang")['code']
        results = self.wiki.search(query, lang=lang)
        try:
            wiki_page = self.wiki.get_page(results[0])
            disambiguation = self.wiki.get_disambiguation_page(results)
        except DisambiguationError:
            # Some disambiguation pages aren't explicitly labelled.
            # The only guaranteed way to know is to fetch the page.
            # Eg "George Church"
            wiki_page = self.wiki.get_page(results[1])
            disambiguation = results[0]
        except HTTPError as error:
            self.log.exception(error)
            raise error
        return wiki_page, disambiguation

    def get_cqs_match_image(self):
        """Fetch the image for a CQS answer.

        This is called from a scheduled event to run in its own thread,
        preventing delays in Common Query answer selection.
        """
        page = self._cqs_match.page
        image = self.wiki.get_best_image_url(page)
        self._cqs_match = self._cqs_match._replace(image=image)

    def handle_disambiguation(self, disambiguation_title: str) -> MediaWikiPage:
        """Ask user which of the different matches should be used.

        Args:
            disambiguation_title: name of disambiguation page
        Returns:
            wikipedia page selected by the user
        """
        try:
            self.wiki.get_page(disambiguation_title)
        except DisambiguationError as disambiguation:
            self.log.info(disambiguation.options)
            self.log.info(disambiguation.details)
            options = disambiguation.options[:3]
            self.speak_dialog('disambiguate-intro')
            choice = self.ask_selection(options)
            self.log.info('Disambiguation choice is {}'.format(choice))
            try:
                wiki_page = self.wiki.get_page(choice)
            except HTTPError as error:
                self.log.exception(error)
                raise error
            return wiki_page

    def handle_result(self, page: MediaWikiPage):
        """Handle result depending on result type.

        Speaks appropriate feedback to user depending of the result type.
        Arguments:
            page: wiki page for search result
        """
        if page is None:
            self.report_no_match()
        else:
            self.report_match(page)

    def report_no_match(self):
        """Answer no match found."""
        self.speak_dialog("no entry found")

    def report_match(self, page: MediaWikiPage):
        """Read short summary to user."""
        summary, num_lines = self.wiki.get_summary_intro(page)
        self.speak(summary)
        article = Article(page.title, page, summary, num_lines)
        self.display_article(article)
        image = self.wiki.get_best_image_url(page)
        article = article._replace(image=image)
        self.update_display_data(article)
        # Remember context and speak results
        self._match = article
        # TODO improve context handling
        self.set_context("wiki_article", "")

    def display_article(self, article: Article):
        """Display the match page on a GUI if connected.

        Arguments:
            article: Article containing necessary fields
        """
        self.gui.clear()
        self.gui['title'] = article.title or ''
        self.gui['summary'] = article.summary or ''
        self.gui['imgLink'] = article.image or ''
        self.log.info(self.gui['summary'])
        self._show_pages(['feature_image', 'summary'], override_idle=60)

    def update_display_data(self, article: Article):
        """Update the GUI display data when a page is already being shown.

        Arguments:
            article: Article containing necessary fields
        """
        self.gui['title'] = article.title or ''
        self.gui['summary'] = article.summary or ''
        self.gui['imgLink'] = article.image or ''

    def _show_pages(self, page_names: list([str]), override_idle: bool = None):
        """Display the correct page depending on the platform.

        Args:
            page_names: the base part of the QML file name is the same
                        regardless of platform.
            override_idle: whether or not the screen to show should override
                           the resting screen.
        """
        if self.platform == 'mycroft_mark_2':
            page_name_suffix = "_mark_ii"
        else:
            page_name_suffix = "_scalable"
        platform_page_names = [f'{page_name}{page_name_suffix}.qml' for page_name in page_names]
        # page_name = page_name_prefix + page_name_suffix + ".qml"
        self.log.info(platform_page_names)

        if override_idle is not None:
            self.gui.show_pages(platform_page_names, override_idle=override_idle)
        else:
            self.gui.show_pages(platform_page_names)

    def stop(self):
        self.gui.release()


def create_skill():
    return WikipediaSkill()
