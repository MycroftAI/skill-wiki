Feature: mycroft-wiki

  Scenario: first world war
    Given an english speaking user
     When the user says "tell me about the first world war"
     Then "mycroft-wiki" should reply with dialog from "searching.dialog"
