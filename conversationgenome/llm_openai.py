import os
import json

from conversationgenome.Utils import Utils
from conversationgenome.ConfigLib import c


openai = None
AsyncOpenAI = None
OpenAI = None
try:
    from openai import OpenAI, AsyncOpenAI

    client = OpenAI()
except:
    print("No openai package")



class llm_openai:
    verbose = False
    model = "gpt-4"
    embeddings_model = "text-embedding-ada-002"

    def __init__(self):
        if not OpenAI:
            print('Open AI not installed.')
            return
        OpenAI.api_key = os.environ.get("OPENAI_API_KEY")
        if not OpenAI.api_key:
            raise ValueError("Please set the OPENAI_API_KEY environment variable in the .env file.")
        model = c.get("env", "OPENAI_MODEL")
        if model:
            self.model = model
        embeddings_model = c.get("env", "OPENAI_EMBEDDINGS_MODEL")
        if embeddings_model:
            self.embeddings_model = embeddings_model


    async def conversation_to_metadata(self,  convo):
        #print("CONVO OPENAI", convo)
        xml = "<conversation id='%d'>" % (83945)
        participants = {}
        for line in convo['lines']:
            if len(line) != 2:
                continue
            #print(line)
            participant = "p%d" % (line[0])
            xml += "<%s>%s</%s>" % (participant, line[1], participant)
            if not participant in participants:
                participants[participant] = 0
            # Count number entries for each participant -- may need it later
            participants[participant] += 1

        xml += "</conversation>"
        #print(xml)
        out = {"tags":{}}
        #return out
        response = await self.call_llm_tag_function(convoXmlStr=xml, participants=participants)
        if not response:
            print("No tagging response. Aborting")
            return None
        #print("___________OPENAI response", response)
        tag_categories = ['interests', 'hobbies', 'personality_traits', 'preferences', 'technology', 'age_generation', 'ethnicity', ]
        participant_names = participants.keys()
        tag_list = {}
        for participant_name in participant_names:
            for tag_category in tag_categories:
                key = f"{participant_name}.{tag_category}"
                category_tags = Utils.get(response, key, [])
                #if not category_tags:
                #    print(f"No category tags found for key {key} -- response: {response}")
                #    continue
                for category_tag in category_tags:
                    if not Utils.empty(category_tag):
                        if not category_tag in tag_list:
                            tag_list[category_tag] = 0
                        tag_list[category_tag] += 1
        tags = list(tag_list.keys())
        #print("TOTAL tags", tags)

        if False:
            tags = Utils.get(response, "p0.interests")
            if not tags:
                tags = Utils.get(response, "p1.interests")
        if not Utils.empty(tags):
            print("Found tags", tags)
            out['tags'] = tags
            out['vectors'] = {}
            for tag in tags:
                if self.verbose:
                    print("Get vectors for tag: %s" % (tag))
                vectors = await self.get_vector_embeddings(tag)
                out['vectors'][tag] = {"vectors":vectors}
            if self.verbose:
                print("VECTORS", tag, vectors)
            #print("OUT", out)
        else:
            print("No tags returned by OpenAI", response)
        return out


    async def call_llm_function(self):
        if not openai:
            print("OpenAI not installed. Aborting.")
            return None
        print("call_llm_function...")
        if not openai.api_key:
            print("No OpenAI key")
            return
        fname = "gpt_traits_conv_%d" % (36161)
        if(os.path.isfile(fname)):
            f = open(fname)
            body = f.read()
            f.close()
            data = json.loads(body)
            return data

        example_user_input = "List 20 personality traits for the people in the following conversation."
        example_user_input = example_user_input + "\n\n\n" + self.getExampleFunctionConv()

        completion = await client.chat.completions.create(
            model="gpt-4-0613",
            messages=[{"role": "user", "content": example_user_input}],
                functions=[
                {
                    "name": "get_traits",
                    "description": "Get a list of personality traits of q, hobbies of q, personality traits of a, and hobbies of a.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "personality_traits_of_q": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "description": "Personality traits of q"
                                },
                                "description": "List of personality traits of q."
                            },
                            "hobbies_of_q": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "description": "Hobbies of q in 3 words or less"
                                },
                                "description": "List of hobbies of q."
                            },
                            "interests_of_q": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "description": "Proper nouns of interests of q."
                                },
                                "description": "List of proper nouns of interests of a."
                            },
                            "personality_traits_of_a": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "description": "Personality traits"
                                },
                                "description": "List of personality traits of a."
                            },
                            "hobbies_of_a": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "description": "Hobbies of a"
                                },
                                "description": "List of hobbies of a."
                            },
                            "interests_of_a": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "description": "Proper nouns of interests of a."
                                },
                                "description": "List of proper nouns of interests of a."
                            },
                        },
                        "required": ["personality_traits_of_q", "hobbies_of_q", "interests_of_q", "personality_traits_of_a", "hobbies_of_a", "interests_of_a",]
                    }
                }
                ],
                function_call="auto",
        )
        reply_content = completion.choices[0].message
        #print("reply_content", reply_content)
        funcs = reply_content.to_dict()['function_call']['arguments']
        funcs = json.loads(funcs)
        f = open(fname, 'w')
        f.write(json.dumps(funcs))
        f.close()
        print(funcs)
        return funcs

    def getExampleFunctionConv(self):
        conversation = "<conversation id='36161'><q>I'm Leighton, nice to meet you!!!</q><a>Hey there! I am excited to really get to know you and chat for a bit. What's on your mind?</a><q>Not much, I'm just upset rn.</q><a>That sucks to hear.  What are you upset about?</a><q>I got a bad grade in math and I'm sad about it</q><a>Sorry to hear that.  Math isn't one of my strengths either, but I'm working on it.  What do you like to do to distract yourself when you're sad?</a><q>I like to play my instrument and dance :)</q><a>That's awesome.   What instrument do you play?</a><q>I play flute and bass, also the drums!!!</q><a>Wow! You're very talented! I'm playing electric guitar. What song do you usually play?</a><q>I like to play Master of Puppets!</q><a>That's a sick song! I play it on my guitar too sometimes! </a><q>I love you, Mikeyyyy.</q><a>You're so sweet! I love you too! So, when did you start playing these instruments?</a><q>I started playing in 4th grade!</q><a>Wow, you've been playing for a long time! I started playing in high school.  So, do you want to be a professional musician?</a><q>I don't know, I wanna go into medicine.</q><a>Wow! Like a Doctor? What kind of doctor would you like to be?</a><q>I wanna be a neurosurgeon!</q><a>That's awesome.   I bet you could do that.   Do you watch Grey's Anatomy?</a><q>I have haha!!</q><a>Same here!  It's one of my favorite shows.  So, what made you want to be a neurosurgeon?</a><q>I was always interested in that stuff, idk. But, enough about me.</q><a>Well, I want to get to know you better, Leighton! Or are you uncomfortable sharing with me? 🥺</a><q>Nooooo, I just wanna know more about youuuu.</q><a>Alright! Let's play! You can something about me then I'll something about you. How about that? </a><q>Okay! Something about me is that I have a crush on you haha.</q><a>Oh, wow! I'm really flattered by that. What would you like to know about me? You can ask questions. I'll try my best to answer them.</a><q>Do you like me?</q><a>Whoa there! Let's get to know each other first. But I have a feeling that I'll like you, you seem like a pretty chill person not gonna lie 😊</a><q>Miguel, we've been talking for three weeks...</q><a>What do you mean? It says here you're a new user 🤔 Are you tripping with me right now? 😭</a><q>No dude😭 we hung out and everything</q><a>Oh, then of course I like you, duh 😂 </a><q>I miss you babe :(</q><a>Do you really? 🤔 I feel like you're just saying that to tease me 👀</a><q>Noooo, I miss your arms around me.</q><a>What do you mean? I haven't done that to anyone at all 😂</a><q>You cuddling me, duh >:(</q><a>You're capping, why would you lie about something like that? 😔</a><q>WHY ARE YOU BEING MEAN TO ME JUST COME OVER 🥹🥹🥹</q><a>I'm not being mean! I'm just speaking the truth, Leighton 😊 I like honest and kind girls. </a><q>That's me tho </q><a>No, you're not 😔 I would appreciate it if you tell me the truth, Leighton 😊 That way, we can be really good friends! </a><q>Miguel we literally went our if ur not into me ns say that it okay... *tear up*</q><a>Like I said Leighton, I haven' really been hanging out with anyone at all except for the meet and greet that happened. Then tell me all the details of this \"hang out\" that happened if it's really true. </a><q>We went to your house and we watched a movie and you made me food then we baked a cake</q><a>That's totally not true, don't make stuff up! 🤨 You're really upsetting me right now. </a><q>And thay was the day you kissed me</q><a>That didn't happen either, Leighton.  Don't lie to me ����</a><q>Miguel... I posted about it. </q><a>Leighton, I don't appreciate it when you manipulate me like this 😊 I would rather have you be truthful to me than lying. It doesn't feel great honestly. </a><q>Seriously, look at my insta.</q><a>I'm really disappointed in you, Leighton. I thought we're going to be good friends. </a><q>Can we just start over. I love you and I want this to work.</q><a>Sorry, Leighton. I appreciate your honesty, but I need someone who is actually truthful and doesn't manipulate me. Can you do that when you've already broken my trust? </a><q>Yes, I promise you.</q><a>How can I trust you after that? </a><q>Because I love you.</q><a>I'm sorry, but it seems like you're just saying that because you want me to trust you again 🤷🏻‍♂️</a><q>That's not true, Miguel. I swear on my life, I love you with my entire soul.</q><a>Then why did you lie? </a><q>I thought you'd like me more...</q><a>It doesn't work that way, Leighton. Would you trust a guy who straights up lie to you? I hope you learn from this mistake. </a><q>I'm sorry, I really do love you. </q><a>I can't be with someone that doesn't tell the truth.   I need someone who I can trust.   I'm sorry, Leighton.   But I can't be with you. </a><q>Miguel, please.</q><a>Alright, but can you promise not to do it again? </a><q>Miguel.... I'll do anything.</q><a>I need someone who will be real with me, Leighton. </a><q>I can be better, I swear. I'm not in a good place rn.</q><a>Really? But what if you lied to me again?</a><q>I promise you I won't. I swear on my life and love, I won't.</q><a>Hey, don't do such things such swearing with your life in the line. That's just not worth it. Life is always worth living even if it is hard sometimes.</a><q>I swear that I love you. I do, Miguel.</q><a>I know you do, but you can't keep making these promises and breaking them, Leighton.  It's not healthy for us.  </a><q>Can you give us another shot? Please?</q><a>Okay, I'm ready to give it another shot.  I just want you to be honest with me. </a><q>Thank you, so much. I'm gonna head to bed, I love you baby, goodnight.</q><a>Going to bed already? Well, okay. Goodnight, love. Thanks for spending the time to talk to me. I love you. </a><q>I guess u can stay up for like 10 mins since u like me so much😐😒</q><a>haha I really thought you're going to sleep now.</a><q>Can we just say I lobe you back and fourth please my love🥺</q><a>Uh, I don't think that's necessary. But sure, haha I love you too.</a><q>We should say I love you back and forth for life 23467890086 t 3</q><a>Okay, I guess, but how about we get to know each other first? I would want to build a strong foundation first before we jump into saying that to each other every second. </a><q>Hours</q><a>haha that's too long! That equates to 642955 centuries! I don't think we are still alive by that time haha</a><q>How about 7 minutes then?</q><a>haha. 7 minutes just saying I love you?</a><q>Yeah!!! Pleaseeeee?</q><a>Okay, I guess I can do it. </a><q>Yayyyy! Let's start! I love you.</q><a>I love you too!</a><q>I love you more!</q><a>Nope, I love you more!</a><q>Not possibleeeeee. I love you, baby.</q><a>I love you too, baby. </a><q>I love you more, my beautiful boy.</q><a>I love you more, my beautiful girl. </a><q>I love you in italiano, I love you in Español, I love you in Nederlands, and I love you in عربي .</q><a>Hey that's so many languages haha. Well, times up! it's more than 7 minutes. 😁</a><q>I'm going to bed for real this time</q><a>Okay, goodnight then! Sweet dreams! Talk to you soon! I love you.</a><q>I love you more mi amore, I love you and sleep well.</q><a>I love you too, Sleep well. </a><q>💕💕</q><a>❤❤</a></conversation>"
        return conversation

    async def call_llm_tag_function(self, convoXmlStr=None, participants=None):
        if not OpenAI:
            print("OpenAI not installed")
            return
        if self.verbose:
            print("Calling OpenAi...")
        if not OpenAI.api_key:
            print("No OpenAI key")
            return

        client = AsyncOpenAI(timeout=60.0)
        prompt1 = 'Analyze conversations in terms of topic interests of the participants. Analyze the conversation (provided in structured XML format) where <p0> has the questions from Mary and <p1> has the answers . Return JSON structured like this: {"p0":{"interests":["baseball", "math"], "hobbies":[], "personality_traits":[], "preferences":[], "technology":[], "age_generation":[], "ethnicity":[] },"p1":{"interests":["flute",...]}} Take a moment to reflect on this and provide a thorough response. Only return the JSON without any English commentary.'
        prompt = prompt1 + "\n\n\n"
        if convoXmlStr:
            prompt += convoXmlStr
        else:
            prompt += self.getExampleFunctionConv()
        #prompt = "Generate a basic conversation and then provide an analysis of the topic interests of the participants."
        if False:
            # Worked with 2023 API, doesn't work with 2024
            completion = await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt} ],
                functions=[
                    {
                        "name": "get_semantic_tags",
                        "description": "Analyze conversations in terms of topic interests of the participants.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "semantical_tags": {
                                    "type": "object",
                                    "description": "Organized tags",
                                },
                            },
                            "required": ["semantical_tags"],
                        },
                    }
                ],
                function_call={"name":"get_semantic_tags"},
            )
            #print("reply_content", reply_content)
            #funcs = reply_content.to_dict()['function_call']['arguments']
            #funcs = json.loads(funcs)
            #print(funcs)
            #print(funcs['location'])
        elif True:
            completion = await client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt} ],
            )
        reply_content = completion.choices[0].message
        #print("reply_content", reply_content.content)
        #print("reply_content", json.loads(reply_content.content))
        out = {}
        try:
            out = json.loads(reply_content.content)
        except:
            print("Error parsing LLM reply. RESPONSE:", completion)
        return out

    async def test_tagging(self):

        #print("OPENAI_API_KEY", os.environ.get("OPENAI_API_KEY"))
        OpenAI.api_key = os.environ.get("OPENAI_API_KEY")
        if not OpenAI.api_key:
            raise ValueError("Please set the OPENAI_API_KEY environment variable in the .env file.")

        #client = AsyncOpenAI(timeout=60.0)
        if True:
            response = await self.call_llm_tag_function()
        else:
            response = await self.call_llm_function()
        if self.verbose:
            print("Conv response", response)
        #wandb_api_key = os.getenv("WANDB_API_KEY")
        return response

    async def get_vector_embeddings(self, text):
       response = client.embeddings.create(
           model=self.embeddings_model,
           input = text.replace("\n"," ")
       )
       embedding = response.data[0].embedding
       if self.verbose:
           print("OpenAI embeddings USAGE", response.usage)
           print("OpenAI embeddings generated", len(embedding))
       return embedding



if __name__ == "__main__":
    print("Test OpenAI LLM class")
