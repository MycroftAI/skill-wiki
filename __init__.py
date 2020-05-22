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


from mycroft.skills.core import (MycroftSkill, intent_handler,
                                 intent_file_handler)


EXCLUDED_IMAGES = [
    'https://upload.wikimedia.org/wikipedia/commons/7/73/Blue_pencil.svg'
]


def wiki_image(pagetext):
    """ Fetch first best image from results.
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


class WikipediaSkill(MycroftSkill):
    def __init__(self):
        super(WikipediaSkill, self).__init__(name="WikipediaSkill")

    @intent_handler(IntentBuilder("").require("FullSummary").
                    require("ArticleTitle"))
    def handle_fullwiki_query(self, message):
        """ Same as above, but says the entire summary outright
        """
        # Talk to the user, as this can take a little time...
        search = message.data.get("ArticleTitle")
        self.speak_dialog("searching", {"query": search})

        try:
            self._lookupfull(search)
        except wiki.PageError:
            self._lookupfull(search, auto_suggest=False)
        except Exception as e:
            self.log.error("Error: {0}".format(e))

    @intent_handler(IntentBuilder("").require("Wikipedia").
                    require("ArticleTitle"))
    def handle_wiki_query(self, message):
        """ Extract what the user asked about and reply with info
            from wikipedia.
        """
        # Talk to the user, as this can take a little time...
        search = message.data.get("ArticleTitle")
        self.speak_dialog("searching", {"query": search})

        try:
            self._lookup(search)
        except wiki.PageError:
            self._lookup(search, auto_suggest=False)
        except Exception as e:
            self.log.error("Error: {0}".format(e))
    
    @intent_handler(IntentBuilder("").require("More").
                    require("wiki_article").require("spoken_lines"))
    def handle_tell_more(self, message):
        """ Follow up query handler, "tell me more".
            If a "spoken_lines" entry exists in the active contexts
            this can be triggered.
        """
        # Read more of the last article queried
        results = self.results
        article = message.data.get("wiki_article")
        lines_spoken_already = int(message.data.get("spoken_lines"))

        summary_read = wiki.summary(article, lines_spoken_already)
        try:
            summary = wiki.summary(article, lines_spoken_already + 5)
        except wiki.PageError:
            summary = wiki.summary(article, lines_spoken_already + 5,
                                   auto_suggest=False)
    @intent_handler(IntentBuilder("").require("WhatSection").
                    one_of("ArticleTitle", "wiki_article"))
    def handle_whatsection_query(self, message):
      """tells about sections 
      """
      article = message.data.get("ArticleTitle")
      if article is not None:
          r = wiki.search(article)
          a = wiki.page(r)
      else: 
          r = message.data.get("wiki_article")
          a = wiki.page(r)
      self.speak_dialog("sections_search", {"query": r})
      sections = a.sections
      self.speak("The sections I found for this are")
      print(sections)
      for i in sections:
        self.speak(i)
      
    
    @intent_handler(IntentBuilder("").require("ReadSection").
                    one_of("ArticleTitle1", "wiki_article").
                    require("Section"))
    def handle_section_query(self, message):
      """reads requested section
      """
      sInput = message.data.get("Section")
      article = message.data.get("wiki_article")
      if article is not None:
        a = wiki.page(article)
        section = a.section(sInput.capitalize())
        if section is not None:
          self.speak_dialog(section)
        else: 
          self.speak_dialog("Sorry, that section does not exist")
        return
      article = message.data.get("ArticleTitle")
      r = wiki.search(article, 1)
      a = wiki.page(r)
      section = a.section(sInput.capitalize())
      if section is not None:
          self.speak_dialog(section)
      else: 
          self.speak_dialog("Sorry, that section does not exist")
          
    @intent_handler(IntentBuilder("").require("Sort").
                    one_of("ArticleTitle2", "wiki_article").
                    require("Word"))
    def handle_word_search(self, message):
      """reads through the page and finds mentions of requested words or phrases
      """
      word = message.data.get("Word")
      article = message.data.get("wiki_article")
      if article is None:
        article = message.data.get("ArticleTitle2")
      r = wiki.search(article, 1)
      a = wiki.page(r)
      sectionI = []
      inSummary = False
      for i in a.summary:
        if i == word:
          inSummary = True
      for i in a.sections:
        for j in a.section(i):
          if j == word:
            sectionI.append(i)
      if inSummary:
        self.speak("The word was found in the summary and", i, ". Would you like me to read the sections?")
      else:
        self.speak("The word was found in", i, ". Would you like me to read the sections?")
        

    @intent_file_handler("Random.intent")
    def handle_random_intent(self, message):
        """ Get a random wiki page.
            Uses the Special:Random page of wikipedia
        """
        # Talk to the user, as this can take a little time...
        search = wiki.random(pages=1)
        self.speak_dialog("searching", {"query": search})
        self._lookup(search)

    def _lookup(self, search, auto_suggest=True):
        """ Performs a wikipedia lookup and replies to the user.
            Arguments:
                search: phrase to search for
        """
        try:
            # Use the version of Wikipedia appropriate to the request language
            dict = self.translate_namedvalues("wikipedia_lang")
            wiki.set_lang(dict["code"])

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
            summary = wiki.summary(results[0], lines,
                                   auto_suggest=auto_suggest)

            if "==" in summary or len(summary) > 250:
                # We hit the end of the article summary or hit a really long
                # one.  Reduce to first line.
                lines = 1
                summary = wiki.summary(results[0], lines,
                                       auto_suggest=auto_suggest)

            # Now clean up the text and for speaking.  Remove words between
            # parenthesis and brackets.  Wikipedia often includes birthdates
            # in the article title, which breaks up the text badly.
            summary = re.sub(r'\([^)]*\)|/[^/]*/', '', summary)

            # Send to generate displays
            self.gui.clear()
            pagetext = wiki.page(results[0], auto_suggest=auto_suggest)
            self.gui['summary'] = summary
            self.gui['imgLink'] = wiki_image(pagetext)
            self.gui.show_page("WikipediaDelegate.qml", override_idle=60)

            # Remember context and speak results
            self.set_context("wiki_article", results[0])
            self.set_context("spoken_lines", str(lines))
            self.speak(summary)
            self.results = results

        except wiki.exceptions.DisambiguationError as e:
            # Test:  "tell me about john"
            options = e.options[:5]

            option_list = (", ".join(options[:-1]) + " " +
                           self.translate("or") + " " + options[-1])
            choice = self.get_response('disambiguate',
                                       data={"options": option_list})
            if choice:
                self._lookup(choice, auto_suggest=auto_suggest)
    def _lookupfull(self, search, auto_suggest=True):
        """ 
        """
        try:
            # Use the version of Wikipedia appropriate to the request language
            dict = self.translate_namedvalues("wikipedia_lang")
            wiki.set_lang(dict["code"])

            # First step is to get wiki article titles.  This comes back
            # as a list.  I.e. "beans" returns ['beans',
            #     'Beans, Beans the Music Fruit', 'Phaseolus vulgaris',
            #     'Baked beans', 'Navy beans']
            results = wiki.search(search, 5)
            if len(results) == 0:
                self.speak_dialog("no entry found")
                return
            #Tells full summary
            summary = wiki.summary(results[0],
                                   auto_suggest=auto_suggest)

            # Now clean up the text and for speaking.  Remove words between
            # parenthesis and brackets.  Wikipedia often includes birthdates
            # in the article title, which breaks up the text badly.
            summary = re.sub(r'\([^)]*\)|/[^/]*/', '', summary)

            # Send to generate displays
            self.gui.clear()
            pagetext = wiki.page(results[0], auto_suggest=auto_suggest)
            self.gui['summary'] = summary
            self.gui['imgLink'] = wiki_image(pagetext)
            self.gui.show_page("WikipediaDelegate.qml", override_idle=60)

            # Remember context and speak results
            self.set_context("wiki_article", results[0])
            self.speak(summary)
            self.results = results

        except wiki.exceptions.DisambiguationError as e:
            # Test:  "tell me about john"
            options = e.options[:5]

            option_list = (", ".join(options[:-1]) + " " +
                           self.translate("or") + " " + options[-1])
            choice = self.get_response('disambiguate',
                                       data={"options": option_list})
            if choice:
                self._lookup(choice, auto_suggest=auto_suggest)


def create_skill():
    return WikipediaSkill()
