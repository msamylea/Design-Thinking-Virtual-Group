from langchain_openai import ChatOpenAI
from openai import OpenAI


completions_model = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

model = ChatOpenAI(model="l3custom", base_url="http://localhost:11434/v1", api_key="ollama")