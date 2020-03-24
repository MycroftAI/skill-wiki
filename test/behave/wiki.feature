Feature: Wikipedia Skill

  Scenario Outline: user asks a question about a person
    Given an english speaking user
     When the user says "<tell me about a person>"
     Then "skill-wiki" should reply with dialog from "searching.dialog"
     And mycroft reply should contain "<person>"

  Examples: user asks a question about a person
    | tell me about a person | person |
    | tell me about abraham lincoln | lincoln |
    | tell me about nelson mandela | mandela |
    | tell me about queen elizabeth | elizabeth |
    | tell me about Mahatma Gandhi | gandhi |
    | tell me about the president of the united states | president |
    | tell me about the secretary general of the united nations | secretary |

  @xfail
  Scenario Outline: Failing user asks a question about a person
    Given an english speaking user
     When the user says "<tell me about a person>"
     Then "skill-wiki" should reply with dialog from "searching.dialog"
     And mycroft reply should contain "<person>"

  Examples: user asks a question about a person
    | tell me about a person | person |
    | tell me about George Church | church |

  Scenario Outline: user asks a question about a place
    Given an english speaking user
     When the user says "<tell me about a place>"
     Then "mycroft-wiki" should reply with dialog from "searching.dialog"
     And mycroft reply should contain "<place>"

  Examples: user asks a question about a place
    | tell me about a place | place |
    | tell me about amsterdam | netherlands |
    | tell me about tokyo | japan |
    | tell me about antarctica | pole |
    | tell me about sandwiches | sandwich |

  Scenario Outline: user asks a question about something
    Given an english speaking user
     When the user says "<tell me about a thing>"
     Then "mycroft-wiki" should reply with dialog from "searching.dialog"
     And mycroft reply should contain "<thing>"

  Examples: user asks a question about a place
    | tell me about a thing | thing |
    | tell me about sandwiches | sandwich |
    | tell me about hammers | hammer |

  @xfail
  # Jira MS-79 https://mycroft.atlassian.net/browse/MS-79
  Scenario Outline: failing queries
    Given an english speaking user
     When the user says "<tell me about failures>"
     Then "mycroft-wiki" should reply with dialog from "searching.dialog"
     And mycroft reply should contain "<failure>"

  Examples: failing things
    | tell me about failures | failure |
    | tell me about automobiles | automobile |

  Scenario Outline: user asks a question about an idea
    Given an english speaking user
     When the user says "<tell me about an idea>"
     Then "mycroft-wiki" should reply with dialog from "searching.dialog"
     And mycroft reply should contain "<idea>"

  Examples: user asks a question about a place
    | tell me about an idea | idea |
    | tell me about philosophy | philosophy |
    | tell me about politics | politics |
    | tell me about science | knowledge |
