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
import json
import re
import wikipedia as wiki
from adapt.intent import IntentBuilder
from mycroft import MycroftSkill, intent_handler


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
        lines = 2
        summary = wiki.summary(result, lines, auto_suggest=auto_suggest)

        if "==" in summary or len(summary) > 250:
            # We hit the end of the article summary or hit a really long
            # one.  Reduce to first line.
            lines = 1
            summary = wiki.summary(result, lines, auto_suggest=auto_suggest)

        # Clean text to make it more speakable
        return re.sub(r'\([^)]*\)|/[^/]*/', '', summary), lines

    def serialize(self):
        """Serialize the object to string.

        Returns:
            (str) string represenation of the object
        """
        return json.dumps(self.__dict__)

    @classmethod
    def deserialize(cls, data):
        """Create a PageMatch object from serialized version."""
        input_dict = json.loads(data)
        return cls(result=input_dict['wiki_result'],
                   auto_suggest=input_dict['auto_suggest'],
                   summary=input_dict['summary'],
                   lines=input_dict['lines'],
                   image=input_dict['image']
                   )


class WikipediaSkill(MycroftSkill):
    def __init__(self):
        super(WikipediaSkill, self).__init__(name="WikipediaSkill")

    @intent_handler(IntentBuilder("").require("Wikipedia").
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
        self.set_context("wiki_article", match.serialize())
        self.set_context("spoken_lines", str(match.lines))
        self.speak(match.summary)

    def respond_disambiguation(self, disambiguation):
        """Ask for which of the different matches should be used."""

        options = (", ".join(disambiguation.options[:-1]) + " " +
                   self.translate("or") + " " + disambiguation.options[-1])

        choice = self.get_response('disambiguate', data={"options": options})

        self.log.info('Disambiguation choice is {}'.format(choice))
        if choice:
            self.handle_result(self.get_wiki_result(choice))

    @intent_handler(IntentBuilder("").require("More").
                    require("wiki_article").require("spoken_lines"))
    def handle_tell_more(self, message):
        """Follow up query handler, "tell me more".

        If a "spoken_lines" entry exists in the active contexts
        this can be triggered.
        """
        # Read more of the last article queried
        article = PageMatch.deserialize(message.data.get("wiki_article"))
        lines_spoken_already = int(message.data.get("spoken_lines"))

        summary_read = wiki.summary(article.wiki_result, lines_spoken_already)
        summary = wiki.summary(article.wiki_result, lines_spoken_already + 5,
                               article.auto_suggest)

        # Remove already-spoken parts and section titles
        summary = summary[len(summary_read):]
        summary = re.sub(r'\([^)]*\)|/[^/]*/|== [^=]+ ==', '', summary)

        if not summary:
            self.speak_dialog("thats all")
        else:
            self.display_article(article)
            self.speak(summary)
            # Update context
            self.set_context("wiki_article", article.serialize())
            self.set_context("spoken_lines", str(lines_spoken_already+5))

    @intent_handler("Random.intent")
    def handle_random_intent(self, message):
        """ Get a random wiki page.

        Uses the Special:Random page of wikipedia
        """
        # Talk to the user, as this can take a little time...
        search = wiki.random(pages=1)
        self.speak_dialog("searching", {"query": search})
        self.handle_result(self._lookup(search))

    def get_wiki_result(self, search):
        """Search wiki and Handle disambiguation.

        This runs the auto_suggest and non-auto-suggest versions in parallell
        to improve speed.

        Arguments:
            search (str): String to seach for

        Returns:
            PageMatch, PageDisambiguation or None
        """

        def lookup(auto_suggest):
            try:
                return self._lookup(search, auto_suggest)
            except wiki.PageError:
                return None
            except Exception as e:
                self.log.error("Error: {0}".format(e))
                return None

        with ThreadPoolExecutor() as pool:
            res_auto_suggest, res_without_auto_suggest = (
                list(pool.map(lookup, (True, False)))
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

    def _lookup(self, search, auto_suggest=True):
        """Performs a wikipedia lookup and replies to the user.

        Arguments:
            search: phrase to search for
        Returns:
            PageMatch, PageDisambiguation or None
        """
        try:
            # Use the version of Wikipedia appropriate to the request language
            lang_dict = self.translate_namedvalues("wikipedia_lang")
            wiki.set_lang(lang_dict["code"])

            # First step is to get wiki article titles.  This comes back
            # as a list.  I.e. "beans" returns ['beans',
            #     'Beans, Beans the Music Fruit', 'Phaseolus vulgaris',
            #     'Baked beans', 'Navy beans']
            results = wiki.search(search, 5)
            if len(results) == 0:
                return None

            return PageMatch(results[0], auto_suggest)

        except wiki.exceptions.DisambiguationError as e:
            # Test:  "tell me about john"
            return PageDisambiguation(e.options)


    def display_article(self, match):
        """Display the match page on a GUI if connected.

        Arguments:
            match (PageMatch): wiki page match
        """
        self.gui.clear()
        self.gui['summary'] = match.summary
        self.gui['imgLink'] = match.image
        self.gui.show_page("WikipediaDelegate.qml", override_idle=60)


def create_skill():
    return WikipediaSkill()
