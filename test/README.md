Note, the wiki skill and the duck duck go skill are now common query skills
and as such behave differently than previous versions of the skill. As a 
result the VK tests were restructured a bit. 

Now specific query skills can be called out by name. So for example, the 
utterance "ask wiki bla" will be handled by the wiki skill intent handler.
The response now begins with the dialog "here is your answer from wikipedia" 
so this must be handled first before we can interrogate the contents of the
response.

This is not the case when common query handles the request and wiki wins
the confidence battle. In that case a different response is sent by the 
system to the user and those messages must be processed differently.

Also new to this testing process is the use of the new audio/speak stop
message recently introduced into the tts module. This reduces overall 
test execution time as without this we would be waiting for up to 2 minutes
for a wiki response to be spoken. Now we just stop the tts output once we
get our next speak message.

The person testing was also expanded to meet the Wikipedia.vocab file.

Finally, note these test only test the intent portion of this skill. To
test the skill from the common query perspective see those VK tests.
