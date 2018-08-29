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
import wikipedia as wiki
from adapt.intent import IntentBuilder


from mycroft.skills.core import MycroftSkill, intent_handler, intent_file_handler
from mycroft.util.log import LOG


# Tests:  tell me about john

class WikipediaSkill(MycroftSkill):
    def __init__(self):
        super(WikipediaSkill, self).__init__(name="WikipediaSkill")

    @intent_handler(IntentBuilder("").require("Wikipedia").
                    require("ArticleTitle"))
    def handle_intent(self, message):
        # Extract what the user asked about
        self._lookup(message.data.get("ArticleTitle"))

    @intent_handler(IntentBuilder("").require("More").
                    require("wiki_article").require("spoken_lines"))
    def handle_tell_more(self, message):
        # Read more of the last article queried
        article = message.data.get("wiki_article")
        lines_spoken_already = int(message.data.get("spoken_lines"))

        summary_read = wiki.summary(article, lines_spoken_already)
        summary = wiki.summary(article, lines_spoken_already+5)

        # Remove already-spoken parts and section titles
        summary = summary[len(summary_read):]
        summary = re.sub(r'\([^)]*\)|/[^/]*/|== [^=]+ ==', '', summary)

        if not summary:
            self.speak_dialog("thats all")
        else:
            self.speak(summary)
            self.set_context("wiki_article", article)
            self.set_context("spoken_lines", str(lines_spoken_already+5))

    @intent_file_handler("Random.intent")
    def handle_random_intent(self, message):
        #Get the Special:Random page of wikipedia
        
        self._lookup(wiki.random(pages=1))

    def _lookup(self, search):
        try:
            # Use the version of Wikipedia appropriate to the request language
            dict = self.translate_namedvalues("wikipedia_lang")
            wiki.set_lang(dict["code"])

            # Talk to the user, as this can take a little time...
            self.speak_dialog("searching", {"query": search})

            # First step is to get wiki article titles.  This comes back
            # as a list.  I.e. "beans" returns ['beans',
            #     'Beans, Beans the Music Fruit', 'Phaseolus vulgaris',
            #     'Baked beans', 'Navy beans']
            results = wiki.search(search, 5)
            if len(results) == 0:
                self.speak_dialog("no entry found")
                return

            # Now request the summary for the first (best) match.  Wikipedia
            # writes in inverted-pyramid style, so the first sentence is the
            # most important, the second less important, etc.  Two sentences
            # is all we ever need.
            lines = 2
            summary = wiki.summary(results[0], lines)
            if "==" in summary or len(summary) > 250:
                # We hit the end of the article summary or hit a really long
                # one.  Reduce to first line.
                lines = 1
                summary = wiki.summary(results[0], lines)

            # Now clean up the text and for speaking.  Remove words between
            # parenthesis and brackets.  Wikipedia often includes birthdates
            # in the article title, which breaks up the text badly.
            summary = re.sub(r'\([^)]*\)|/[^/]*/', '', summary)

            # Remember context and speak results
            self.set_context("wiki_article", results[0])
            self.set_context("spoken_lines", str(lines))
            self.speak(summary)

        except wiki.exceptions.DisambiguationError as e:
            # Test:  "tell me about john"
            options = e.options[:5]

            option_list = (", ".join(options[:-1]) + " " +
                           self.translate("or") + " " + options[-1])
            choice = self.get_response('disambiguate',
                                       data={"options": option_list})
            if choice:
                self._lookup(choice)

        except Exception as e:
            LOG.error("Error: {0}".format(e))


def create_skill():
    return WikipediaSkill()
