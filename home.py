# Bring in deps
import os
# import json
from dotenv import load_dotenv
import time
import re
import inflect
import random

import openai
import streamlit as st 
from annotated_text import annotated_text

from langchain.llms import AzureOpenAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores.weaviate import Weaviate

import weaviate
from weaviate import Client


load_dotenv()
# configure Azure OpenAI Service API
openai.api_type = os.getenv("OPENAI_API_TYPE")
openai.api_version = os.getenv("OPENAI_API_VERSION")
openai.api_base = os.getenv("OPENAI_ENDPOINT")
openai.api_key = os.getenv("OPENAI_API_KEY")

# Page title
st.set_page_config(page_title='HateXpel', page_icon=':no_entry_sign:')
st.title(':speaking_head_in_silhouette: :no_entry_sign:  :man-gesturing-no: HateXpel ')

st.write(':warning: **Trigger Warning:** Demonstration contains offensive language, profanities and other potentially distressing content. :warning:')


def typing(text):
    with open("typewriter.html", "r") as f:
        html_content = f.read()
        html_content = html_content.replace("{{ text_to_type }}", text)
        st.components.v1.html(html_content, height=25, scrolling=False)
    time.sleep(0.6)

def get_vector_embedding(text):
    st.divider()
    typing("creating embeddings for your comment ....")
    try:
        response = openai.Embedding.create(
            input=text,
            engine="gf-model-embedding-001"
        )
        embedding = response['data'][0]['embedding']
        if embedding != None:
            st.write("**Vector Embedding:**")
            return embedding
    except Exception as e:
        print(f"Error: {e}")
        return None

def start_vectorstore():
    typing("instantiating vectore store ....")
    client = weaviate.Client(
        url = "http://localhost:8081",  # Replace with your endpoint
        additional_headers = {
            "X-Azure-Api-Key": os.getenv("OPENAI_API_KEY")
        }
    )
    if client.is_ready():
        typing("vector store loaded ....")
        db = Weaviate(client=client, index_name="NewDataClass", text_key="content")
        return db

def generate_response(db, input_text):

    #llm
    load_dotenv()
    # create an instance of Azure OpenAI
    llm = AzureOpenAI(
        deployment_name=os.getenv("OPENAI_DEPLOYMENT_NAME"),
        model_name=os.getenv("OPENAI_MODEL"), 
        openai_api_version=os.getenv("OPENAI_API_VERSION"),
        temperature=0.0
    )

    # configure prompt template
    hatespeech_template= """
    You are a professional, specialised in reviewing abusive content which could violate sections 298 and 298A of Singapore's penal code.
    Section 298 of the Penal Code is a charge for uttering words, etc., with deliberate intent to wound the religious or racial feelings of any person.
    Section 298A of the Penal Code is a charge for promoting enmity between different groups on grounds of religion or race or doing acts prejudicial to maintenance of harmony.
    Hate speech has been defined as all forms of expression which spread, incite, promote, or justify racial hatred, xenophobia, or other forms of hatred based on intolerance.
    Your instruction is to first evaluate and provide explanation if the given comment is considered a hate speech or not. If it is not a hate speech, explain why it is not a hate speech.
    Secondly, identify the possible core identity groups and the sub identity groups from the comment.
    Use only the context given below to carry out the task. If you don't know the answer, just say you don't know the answer.

    Here is the context:
    {context}

    Here is the comment:
    {comment}

    Complete your answer in the following format:
    [Explanation:]
    This comment {comment} targets the following core identity groups: [answer] and the following sub identity groups: [answer].
    """
    prompt_template = PromptTemplate(
    input_variables=['context', 'comment'],
    template=hatespeech_template)
    
    # create QA LangChain
    qa_chain = load_qa_chain(llm, chain_type="stuff", prompt=prompt_template)

    # similarity serach via LangChain
    typing("calculating cosine similarity ....")
    typing("fetching semantically similar documents ....")
    docs = db.similarity_search_by_text(input_text)
    st.write("**Documents:**")
    st.write(docs)
    
    st.write("**Extracted Comments:**")
    for i, v in enumerate(docs):
        st.code(f"{i+1}. { v.page_content }")
    
    output = qa_chain({"input_documents": docs, "comment": input_text}, return_only_outputs=True)

    typing("running few-shot prompts ....")
    typing("fetching results ....")
    st.divider()
    st.write("**Result:**")
    return output['output_text']
    
def clear_form():
    st.session_state["text"] = ""


##### FORM UI #####
text = st.text_area(
    label="Check your comment here:",
    max_chars=200,
    key="text"
    )

submitted = st.button("Submit")
cleared = st.button(label="Clear", on_click=clear_form)

def colour_write(output):
    anno_list = ['core identity', 'sub identity', 'hate speech', 'not',
                 'race', 'ethnicity', 'black', 'african american', 'latino', 'non-white', 'hispanic', 'asian', 
                 'middle eastern', 'native american', 'alaska native', 'pacific islander', 'non-hispanic white',
                 'religion', 'jews', 'christians', 'buddhists', 'hindus','mormons', 'atheists', 'muslims', 'national origin', 
                 'citizenship', 'specific country', 'immigrant', 'migrant worker', 'undocumented person', 'gender',
                 'women', 'men', 'non-binary', 'third gender', 'transgender women', 'transgender men', 'transgender', 'sexual orientation', 
                 'bisexual', 'gay', 'lesbian', 'heterosexual', 'age', 'children', 'adolescents/teenagers', 'young adults/adults', 
                 'middle-aged', 'seniors', 'disability', 'disabilities', 'cognitive disorders', 'autism', 'down syndrome', 'mental health', 'depression',
                 'visually impaired', 'hearing impaired', 'chinese', 'malay', 'muslim', 'indian', 'nationality', 'country', 'Singapore', 'sexuality']
    
    colors = ['blue', 'green', 'violet', 'orange']

    p = inflect.engine()
    plural_forms = [p.plural(word) for word in anno_list]
    anno_list = anno_list + plural_forms

    for term in anno_list:
        # Escape any special characters in the term for regex matching
        escaped_term = re.escape(term)
        # for cases where it talks about hate or non hate
        anno_list_special = ['not', 'hate speech', 'non hate speech', 'non hate', 'hate comment']
        if term in anno_list_special:
            output = re.sub(r'(?i)\b' + escaped_term + r'\b', f"***:red[{term}]***", output)
        else:
            # Randomly select a color
            color = random.choice(colors)
            # Use a case-insensitive regex search and replace
            output = re.sub(r'(?i)\b' + escaped_term + r'\b', f"**:{color}[{term}]**", output)

    st.markdown(output)

##### MAIN CALL #####
if submitted:
    st.code(get_vector_embedding(text))
    db = start_vectorstore()
    output = generate_response(db, text)
    colour_write(output)