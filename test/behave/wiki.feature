Feature: Wikipedia Skill

  Scenario Outline: user asks a question about a person
    Given an english speaking user
     When the user says "<tell me about a person>"
     Then "skill-wiki" should reply with dialog "wiki.specific.response.dialog"
     When dialog is stopped
     Then mycroft reply should contain "<person>"

  Examples: user asks a question about a person
    | tell me about a person | person |
    | tell me about the president of the united states | president |
    | ask wiki who was abraham lincoln | lincoln |
    | ask wiki who were the beatles | beatles |
    | tell me who was alexander the great | alexander |
    | tell us about nelson mandela | mandela |
    | ask wikipedia who is queen elizabeth | elizabeth |
    | what does wikipedia say about Mahatma Gandhi | gandhi |
    | what does wiki say about al capone | capone |
    | ask wiki what is the secretary general of the united nations | secretary |
    | tell me who is the secretary general of the united nations | secretary |


  Scenario Outline: user asks a question about a person
    Given an english speaking user
     When the user says "<tell me about a person>"
     Then "skill-wiki" should reply with dialog "wiki.specific.response.dialog"
     When dialog is stopped
     Then mycroft reply should contain "<person>"

  Examples: user asks a question about a person
    | tell me about a person | person |
    | tell me about George Church | church |


  Scenario Outline: user asks a question about a place
    Given an english speaking user
     When the user says "<tell me about a place>"
     Then "skill-wiki" should reply with dialog "wiki.specific.response.dialog"
     When dialog is stopped
     Then mycroft reply should contain "<place>"

  Examples: user asks a question about a place
    | tell me about a place | place |
    | tell me about amsterdam | netherlands |
    | tell me about tokyo | japan |
    | tell me about antarctica | pole |


  Scenario Outline: user asks a question about a something
    Given an english speaking user
     When the user says "<tell me about a thing>"
     Then "skill-wiki" should reply with dialog "wiki.specific.response.dialog"
     When dialog is stopped
     Then mycroft reply should contain "<thing>"

  Examples: user asks a question about a thing
    | tell me about a thing | thing |
    | tell me about sandwiches | sandwich |
    | tell me about hammers | hammer |
    | ask wikipedia what is an automobile | car |
    | ask wiki what is a car | car |
    | what can wiki tell us about failures | failure |


  Scenario Outline: user asks a question about an idea
    Given an english speaking user
     When the user says "<tell me about an idea>"
     Then "skill-wiki" should reply with dialog "wiki.specific.response.dialog"
     When dialog is stopped
     Then mycroft reply should contain "<idea>"

  Examples: user asks a question about an idea
    | tell me about an idea | idea |
    | tell me about philosophy | philosophy |
    | ask wiki what is politics | politics |
    | tell us about science | knowledge |

