from langchain_community.chat_models import ChatLlamaCpp
from pathlib import Path
path = Path("E:/SIH_26/SERVER/Classfication/Models/LLM/Qwen3.5-4B-Q4_K_M.gguf")
llm = ChatLlamaCpp( model_path=str(path),
    n_ctx=4000,
    n_gpu_layers=0,
    verbose=False,
    max_tokens=5000)
chat= llm.invoke("Do you have reasoning capabilities? If yes, then explain the reasoning behind the following statement: 'ek wroker 70 feet hight per 8 pound tool leke tha , niche koi protection nahi tha but vo unchai pe kam kar raha tha , tool rakhne ka jagah nahi tha but tool gir nahi ' if the give statement scalled in serious injured or fatality , then what could be the percentage what are high energy imtem in this scenario and what are the possible mitigation measures to avoid the incident. Please provide your answer in a structured format with bullet points and also explain the reasoning behind your answer.")
print(chat.content)