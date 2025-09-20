from langchain_openai import ChatOpenAI

from config import settings


class ChatService:
    llm = ChatOpenAI(
        temperature=0.6,
        model="glm-4.5",
        openai_api_key=settings.yaml_config.get("zhipu").get("api-key"),
        openai_api_base=settings.yaml_config.get("zhipu").get("base-url")
    )
    @classmethod
    def chat(cls,message):
       resp =  cls.llm.invoke(message)
       print(resp)
