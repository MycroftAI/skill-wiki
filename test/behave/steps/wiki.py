import time 

from behave import then

from mycroft.audio import wait_while_speaking

@then('wait while speaking')
def handle_wait(context):
    # add sleep to ensure there is a delay when using a dummy TTS eg CI
    time.sleep(3)
    wait_while_speaking()