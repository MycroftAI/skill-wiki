Feature: Wikipedia Skill

  Scenario Outline: user asks a question about a person
    Given an english speaking user
     When the user says "<tell me about abraham lincoln>"
     Then "skill-wiki" should reply with dialog from "searching.dialog"
     And mycroft reply should contain "<lincoln>"

  Examples: user asks a question about a person
    | tell me about abraham lincoln | lincoln |
    | tell me about nelson mandela | mandela |
    | tell me about queen elizabeth | elizabeth |
    | tell me about Mahatma Gandhi | gandhi |
    | tell me about George Church | church |
    | tell me about the president of the united states | president |
    | tell me about the secretary general of the united nations | secretary |

  Scenario Outline: user asks a question about a place
    Given an english speaking user
     When the user says "<tell me about amsterdam>"
     Then "mycroft-wiki" should reply with dialog from "searching.dialog"
     And mycroft reply should contain "<netherlands>"

  Examples: user asks a question about a place
    | tell me about amsterdam | netherlands |
    | tell me about tokyo | japan |
    | tell me about antarctica | pole |
    | tell me about sandwiches | sandwich |

  Scenario Outline: user asks a question about something
    Given an english speaking user
     When the user says "<tell me about sandwiches>"
     Then "mycroft-wiki" should reply with dialog from "searching.dialog"
     And mycroft reply should contain "<sandwich>"

  Examples: user asks a question about a place
    | tell me about sandwiches | sandwich |
    | tell me about hammers | hammer |

  @xfail
  Scenario Outline: failing queries
    Given an english speaking user
     When the user says "<tell me about failure>"
     Then "mycroft-wiki" should reply with dialog from "searching.dialog"
     And mycroft reply should contain "<failure>"

  Examples: failing things
    | tell me about failures | failures |
    | tell me about automobiles | automobile |

  Scenario Outline: user asks a question about an idea
    Given an english speaking user
     When the user says "<tell me about philosophy>"
     Then "mycroft-wiki" should reply with dialog from "searching.dialog"
     And mycroft reply should contain "<philosophy>"

  Examples: user asks a question about a place
    | tell me about philosophy | philosophy |
    | tell me about politics | politics |
    | tell me about science | knowledge |
