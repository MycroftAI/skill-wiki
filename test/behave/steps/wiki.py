import time 

from behave import then, when
from mycroft.messagebus import Message
from mycroft.audio import wait_while_speaking
from test.integrationtests.voight_kampff import then_wait

@when('dialog is stopped')
def when_dialog_is_stopped(context):
    context.bus.emit(Message('mycroft.audio.speech.stop',
                             data={},
                             context={}))

@then('"{skill}" should reply with dialog "{dialog}"')
def then_dialog(context, skill, dialog):
    def check_dialog(message):
        utt_dialog = message.data.get('utterance', '')
        return (utt_dialog == 'Here is your answer from wiki peedia', '')

    passed, debug = then_wait('speak', check_dialog, context)
    if not passed:
        assert_msg = debug

    assert passed, assert_msg or 'Mycroft didn\'t respond'
