from behave import then

from mycroft.audio import wait_while_speaking

@then('wait while speaking')
def handle_wait(context):
    wait_while_speaking()