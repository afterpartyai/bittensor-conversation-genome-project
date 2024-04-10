openai = None
try:
    import openai
    from openai import AsyncOpenAI, OpenAI
except:
    print("No openai lib")



class llm_openai:
    def convert(self):
        print("Convert OpenAI")

if __name__ == "__main__":
    print("Test OpenAI LLM class")
